"""Offline wrapper checks. No data substitute, GPU mock, model or training."""
import ast
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

REMOTE = pathlib.Path(__file__).resolve().parent.parent / "secpatch" / "remote"


def module(name):
    spec = importlib.util.spec_from_file_location("remote_" + name, REMOTE / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class RemoteWrapperTests(unittest.TestCase):
    def test_original_pipeline_files_match_recorded_base(self):
        base = json.loads((REMOTE / "SOURCE_BASE.json").read_text())
        for name, expected in base["core_sha256"].items():
            path = REMOTE.parent.parent / name
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected, name)

    def test_payload_tampering_and_path_escape_are_rejected(self):
        run = module("run")
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            file = root / "code.py"
            file.write_text("reviewed source")
            lock = {"files": {"code.py": hashlib.sha256(file.read_bytes()).hexdigest()}}
            run.check_lock(root, lock)
            file.write_text("altered source")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                run.check_lock(root, lock)
            with self.assertRaisesRegex(ValueError, "Unsafe payload path"):
                run.check_lock(root, {"files": {"../secret": "a"*64}})
            file.unlink()
            file.symlink_to(root / "missing")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                run.check_lock(root, lock)

    def test_local_execution_is_refused_before_gpu_import(self):
        result = subprocess.run([sys.executable, str(REMOTE / "run.py"),
                                 "--payload", "/nonexistent", "--output", "/nonexistent"],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("local GPU execution is forbidden", result.stderr)

    def test_notebook_is_unexecuted_and_compiles(self):
        notebook = module("prepare").notebook("a"*64)
        self.assertEqual(notebook["cells"][0]["outputs"], [])
        self.assertIsNone(notebook["cells"][0]["execution_count"])
        ast.parse("".join(notebook["cells"][0]["source"]))

    def test_missing_real_data_fails_before_output_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = pathlib.Path(tmp) / "private-output"
            result = subprocess.run([sys.executable, str(REMOTE / "prepare.py"),
                                     "--data", tmp, "--candidates", tmp+"/absent",
                                     "--harvest", tmp+"/absent", "--osv-archive", tmp+"/absent",
                                     "--owner", "example", "--output", str(dest)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Dataset manifest is required", result.stderr)
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
