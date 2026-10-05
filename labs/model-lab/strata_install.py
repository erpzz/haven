"""Run the exact upstream setup with local-only, prebuilt-only installation bounds.

No upstream files are rewritten. Release/model hashes come from catalog.json,
verified against GitHub release metadata and Hugging Face LFS metadata.
"""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import sys
import threading
import time
import zipfile

from labcore import ROOT, sha256_file, atomic_json, download_verified, Job


def checked_cleanup(path, scope):
    candidate = Path(path).absolute()
    scope = scope.resolve()
    resolved = candidate.resolve()
    if resolved == scope or not resolved.is_relative_to(scope):
        raise ValueError('Upstream cleanup escaped the owned Strata directory.')
    for part in (candidate, *candidate.parents):
        if part == scope.parent:
            break
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise ValueError('Refusing cleanup through a link or junction.')
    if candidate.exists():
        for folder, dirs, _ in os.walk(candidate, followlinks=False):
            for name in dirs:
                child = Path(folder) / name
                if child.is_symlink() or (hasattr(child, 'is_junction') and child.is_junction()):
                    raise ValueError('Refusing recursive cleanup containing a link or junction.')


def configure_install_environment():
    # pip reads command options from PIP_* and user/global pip.ini by default.
    # Neither may redirect this installation's writes or package source.
    for key in list(os.environ):
        if key.startswith(('STRATA_', 'LLAMA_ARG_', 'OPENAI_', 'ANTHROPIC_', 'PIP_', 'HF_')) or key in ('HUGGING_FACE_HUB_TOKEN', 'HUGGINGFACE_HUB_CACHE'):
            os.environ.pop(key, None)
    cache = ROOT / '.local' / 'cache'
    os.environ.update(HF_HOME=str(cache / 'huggingface'), HF_HUB_CACHE=str(cache / 'huggingface/hub'),
                      PIP_CACHE_DIR=str(cache / 'pip'), PIP_CONFIG_FILE=os.devnull,
                      PYTHONUTF8='1', HF_ENDPOINT='https://huggingface.co')


def main():
    source = ROOT / '.local' / 'Strata'
    catalog = json.loads((ROOT / 'catalog.json').read_text('utf-8'))['strata']
    if (source / 'HAVEN_SOURCE_COMMIT.txt').read_text().strip() != catalog['commit']:
        raise ValueError('Strata source identity does not match the catalog.')
    if sha256_file(source / 'setup.py') != catalog['setup_sha256']:
        raise ValueError('Upstream setup.py differs from the verified pinned Git blob.')
    if Path(sys.prefix).resolve() != (source / '.venv').resolve():
        raise ValueError('Run this wrapper only from the isolated Strata venv.')
    configure_install_environment()
    spec = importlib.util.spec_from_file_location('haven_upstream_strata_setup', source / 'setup.py')
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)
    artifacts = {a['url']: a for a in catalog['engine_assets'].values()}
    for model in catalog['models'].values():
        artifacts.update({a['url']: a for a in model})
    original_download = upstream.download
    receipt = ROOT / '.local' / 'strata-artifact-receipts.json'
    receipts = json.loads(receipt.read_text('utf-8')) if receipt.exists() else {}
    hash_cache = {}
    verified_this_run = set()
    model_pins = {Path(a['url']).name: a for values in catalog['models'].values() for a in values}

    def verify_file(path, pin):
        stat = path.stat()
        identity = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
        digest = hash_cache.get(identity)
        if digest is None:
            digest = sha256_file(path); hash_cache[identity] = digest
        if stat.st_size != pin['size_bytes'] or digest != pin['sha256']:
            raise ValueError('Upstream artifact checksum/size mismatch; retained file was not accepted.')
        return digest

    def verified_download(url, destination, what=None):
        pin = artifacts.get(url)
        if pin is None and url != upstream.LLAMA_CPP_ZIP:
            raise ValueError('Unreviewed upstream artifact; add verified provenance before downloading.')
        if pin:
            job = Job('strata-download')
            ended = threading.Event()
            def progress():
                while not ended.wait(10):
                    current = job.snapshot()
                    fraction = current.get('progress')
                    status = f'{fraction:.0%}' if fraction is not None else current.get('message', 'starting')
                    print(f'{what or destination.name}: {status}', flush=True)
            thread = threading.Thread(target=progress, daemon=True)
            thread.start()
            try:
                download_verified(url, destination, pin['sha256'], pin['size_bytes'], job)
                upstream.mark(destination)  # Only verified complete bytes receive the upstream marker.
            finally:
                ended.set()
                thread.join(timeout=1)
        else:
            original_download(url, destination, what)
        digest = verify_file(destination, pin) if pin else sha256_file(destination)
        receipts[url] = {'sha256': digest, 'size_bytes': destination.stat().st_size,
                         'at': time.time(), 'verification': 'PINNED_SHA256' if pin else 'IMMUTABLE_SOURCE_COMMIT'}
        atomic_json(receipt, receipts)
        verified_this_run.add(url)
        print(f'Verified: {destination.name}', flush=True)

    def no_system_build(*args, **kwargs):
        raise RuntimeError('No compatible verified prebuilt engine. System build-tool installation requires an operator decision.')

    original_rmtree = shutil.rmtree
    def owned_rmtree(path, *args, **kwargs):
        checked_cleanup(path, source)
        return original_rmtree(path, *args, **kwargs)

    upstream.download = verified_download
    original_done = upstream.done
    def verified_done(path):
        result = original_done(path)
        pin = model_pins.get(path.name)
        if result and pin: verify_file(path, pin)
        return result
    upstream.done = verified_done
    original_prebuilt = upstream.get_prebuilt
    def verified_prebuilt(*args, **kwargs):
        engine = original_prebuilt(*args, **kwargs)
        if engine is not None:
            manifest = ROOT / '.local' / ('strata-engine-' + engine.name + '-hashes.json')
            actual = {str(p.relative_to(engine)): sha256_file(p) for p in engine.rglob('*')
                      if p.is_file() and p.suffix.lower() in ('.exe', '.dll')}
            if manifest.exists():
                if json.loads(manifest.read_text('utf-8')) != actual:
                    raise ValueError('Installed Strata engine differs from the verified release extraction.')
            else:
                toolkit = str(kwargs.get('toolkit', 13))
                if catalog['engine_assets'][toolkit]['url'] not in verified_this_run:
                    raise ValueError('No verified release receipt for this pre-existing engine.')
                atomic_json(manifest, actual)
        return engine
    upstream.get_prebuilt = verified_prebuilt
    upstream.hf_unpinned = lambda url: url  # A missing revision remains a failure.
    upstream.settings_path = lambda: ROOT / '.local' / 'strata-settings.json'
    upstream.other_installs = lambda settings: []
    def local_data_folder(requested):
        expected = (ROOT / '.local' / 'Strata-data').resolve()
        if requested is None or Path(requested).resolve() != expected:
            raise ValueError('Use the isolated lab Strata-data directory.')
        expected.mkdir(parents=True, exist_ok=True)
        return expected, []
    upstream.data_folder = local_data_folder
    original_run = upstream.run
    def strict_run(argv, *args, **kwargs):
        argv = list(argv)
        if len(argv) > 1 and Path(argv[1]).name == 'mtp_fetch.py':
            argv[1] = str(ROOT / 'strata_mtp.py')
        return original_run(argv, *args, **kwargs)
    upstream.run = strict_run
    upstream.install_build_tools = no_system_build
    upstream.build_engine = no_system_build
    upstream.build_engine_hip = no_system_build
    # The verified prebuilt lane needs no compiler. CMake's documentation tree
    # also exceeds MAX_PATH in an otherwise usable nested Windows workspace.
    original_requirements = upstream.requirement_lines
    upstream.requirement_lines = lambda *args, **kwargs: [
        line for line in original_requirements(*args, **kwargs)
        if upstream.req_name(line) not in ('cmake', 'ninja')]
    upstream.PY_PACKAGES = [name for name in upstream.PY_PACKAGES
                           if name not in ('cmake', 'ninja')]
    def runtime_llama_source():
        # Prebuilt execution only imports gguf-py. Full source extraction includes
        # unrelated benchmark filenames which exceed MAX_PATH on this host.
        checked_cleanup(source / 'third_party', source)
        destination = source / 'third_party' / 'llama-runtime'
        checked_cleanup(destination, source)
        manifest = ROOT / '.local' / 'strata-gguf-py-hashes.json'
        if destination.exists():
            actual = {str(p.relative_to(destination)): sha256_file(p)
                      for p in destination.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
            if not manifest.exists() or json.loads(manifest.read_text('utf-8')) != actual:
                raise ValueError('Reused gguf-py source does not match its verified extraction.')
            return destination
        archive = source / 'third_party' / f'llama.cpp-{upstream.LLAMA_CPP_COMMIT[:7]}.zip'
        verified_download(upstream.LLAMA_CPP_ZIP, archive, 'llama.cpp runtime source')
        staging = source / 'third_party' / 'llama-runtime.staging'
        if staging.exists():
            raise ValueError('Runtime source staging exists; inspect the retained installation.')
        staging.mkdir(parents=True)
        prefix = f'llama.cpp-{upstream.LLAMA_CPP_COMMIT}/'
        with zipfile.ZipFile(archive) as bundle:
            for entry in bundle.infolist():
                relative = entry.filename.removeprefix(prefix)
                if not entry.filename.startswith(prefix) or not (relative.startswith('gguf-py/') or relative == 'LICENSE'):
                    continue
                target = staging / relative
                if '..' in Path(relative).parts or ':' in relative or not target.resolve().is_relative_to(staging.resolve()):
                    raise ValueError('Unsafe pinned runtime source archive member.')
                if entry.is_dir(): target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(bundle.read(entry))
        if not (staging / 'gguf-py' / 'gguf').is_dir():
            raise ValueError('Pinned archive is missing the required gguf-py package.')
        actual = {str(p.relative_to(staging)): sha256_file(p) for p in staging.rglob('*') if p.is_file()}
        staging.replace(destination)
        atomic_json(manifest, actual)
        return destination
    upstream.get_llama_cpp = runtime_llama_source
    shutil.rmtree = owned_rmtree
    sys.argv = ['setup.py', *sys.argv[1:], '--prebuilt',
                f'https://github.com/Niko1221/Strata/releases/download/{catalog["tag"]}/']
    try:
        return upstream.main()
    finally:
        shutil.rmtree = original_rmtree


if __name__ == '__main__':
    raise SystemExit(main())
