"""Small archive/install fixtures; no downloads, GPU calls or model execution."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime_archive import safe_extract_tar
from labcore import Lab


def archive(rows):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode='w:gz') as stream:
        for name, data, kind in rows:
            info = tarfile.TarInfo(name)
            info.mode = 0o755
            if kind in ('symlink', 'hardlink'):
                info.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.LNKTYPE
                info.linkname = data
                stream.addfile(info)
            elif kind == 'fifo':
                info.type = tarfile.FIFOTYPE
                stream.addfile(info)
            else:
                info.size = len(data)
                stream.addfile(info, io.BytesIO(data))
    return out.getvalue()


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def extract(self, rows, limit=1024):
        p = self.root / 'fixture.tar.gz'
        p.write_bytes(archive(rows))
        safe_extract_tar(p, self.root / 'stage', limit)
        return self.root / 'stage'

    def test_internal_library_aliases_become_private_regular_files(self):
        stage = self.extract([
            ('pkg/lib.so.1', b'library', 'file'),
            ('pkg/lib.so.0', 'lib.so.1', 'symlink'),
            ('pkg/lib.so', 'lib.so.0', 'symlink'),
            ('pkg/hard.so', 'pkg/lib.so.1', 'hardlink'),
        ])
        for name in ('lib.so.1', 'lib.so.0', 'lib.so', 'hard.so'):
            p = stage / 'pkg' / name
            self.assertEqual(p.read_bytes(), b'library')
            self.assertFalse(p.is_symlink())
            if os.name != 'nt':
                self.assertEqual(p.stat().st_mode & 0o077, 0)

    def test_traversal_and_absolute_paths_rejected(self):
        for name in ('../outside', '/outside', 'C:/outside', 'pkg\\outside'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.extract([(name, b'bad', 'file')])

    def test_external_and_cyclic_aliases_rejected(self):
        for rows in ([('alias', '../../outside', 'symlink')],
                     [('a', 'b', 'symlink'), ('b', 'a', 'symlink')]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.extract(rows)

    def test_alias_cannot_be_an_archive_parent(self):
        with self.assertRaises(ValueError):
            self.extract([('p', 'target', 'symlink'), ('target', b'x', 'file'), ('p/child', b'x', 'file')])

    def test_special_files_rejected(self):
        with self.assertRaises(ValueError):
            self.extract([('pipe', b'', 'fifo')])

    def test_materialized_aliases_count_toward_size_limit(self):
        with self.assertRaises(ValueError):
            self.extract([('a', b'1234', 'file'), ('b', 'a', 'symlink')], limit=7)

    @unittest.skipIf(os.name == 'nt', 'POSIX staging path boundary')
    def test_existing_stage_link_cannot_redirect_writes(self):
        outside = self.root / 'outside'
        outside.mkdir()
        stage = self.root / 'stage'
        stage.mkdir()
        (stage / 'linked').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.extract([('linked/escape', b'bad', 'file')])
        self.assertFalse((outside / 'escape').exists())


class Response(io.BytesIO):
    status = 200
    def __init__(self, data):
        super().__init__(data)
        self.headers = {'Content-Length': str(len(data))}


@unittest.skipUnless(sys.platform == 'linux', 'Actual Linux installer path')
class LinuxInstallTests(unittest.TestCase):
    def install(self, executable):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        blobs = {
            'https://github.com/fixture/engine.tar.gz': archive([
                ('engine/llama-server', executable, 'file'),
                ('engine/libggml.so.1', b'library', 'file'),
                ('engine/libggml.so', 'libggml.so.1', 'symlink'),
            ]),
            'https://github.com/fixture/runtime.tar.gz': archive([('libcudart.so.12', b'runtime', 'file')]),
        }
        assets = [{'name': u.rsplit('/', 1)[1], 'url': u, 'size_bytes': len(b),
                   'sha256': hashlib.sha256(b).hexdigest()} for u, b in blobs.items()]
        lab = Lab(Path(self.tmp.name), {'models': [], 'llama_tag': 'fixture', 'llama_linux_assets': assets})
        self.addCleanup(lab.shutdown)
        class Opener:
            def open(self, request, timeout):
                return Response(blobs[request.full_url])
        with patch('labcore.urllib.request.build_opener', return_value=Opener()):
            jid = lab.install_llama()
            end = time.monotonic() + 5
            while lab.jobs[jid].snapshot()['state'] == 'RUNNING' and time.monotonic() < end:
                time.sleep(.02)
        return lab, lab.jobs[jid].snapshot()

    def test_linux_install_verifies_extracts_and_colocates_runtime(self):
        lab, result = self.install(b'\x7fELFfixture-not-an-executable')
        self.assertEqual(result['state'], 'COMPLETED', result.get('error'))
        exe = lab.llama_exe()
        self.assertIsNotNone(exe)
        self.assertTrue(os.access(exe, os.X_OK))
        self.assertEqual((exe.parent / 'libcudart.so.12').read_bytes(), b'runtime')
        self.assertFalse((exe.parent / 'libggml.so').is_symlink())
        receipt = json.loads((lab.data / 'engines/fixture/install-receipt.json').read_text())
        self.assertEqual(receipt['platform'], 'linux')
        self.assertEqual(receipt['assets'], lab.catalog['llama_linux_assets'])

    def test_wrong_binary_is_retained_in_stage_not_published(self):
        lab, result = self.install(b'MZ-not-a-linux-engine')
        self.assertEqual(result['state'], 'FAILED')
        self.assertIn('ELF', result['error'])
        self.assertIsNone(lab.llama_exe())
        self.assertTrue((lab.data / 'engines/fixture.staging').is_dir())


if __name__ == '__main__':
    unittest.main()
