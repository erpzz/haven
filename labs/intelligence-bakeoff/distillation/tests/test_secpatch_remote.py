"""Offline wrapper checks. No data substitute, GPU mock, model or training."""
import ast
import base64
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
    def test_source_notices_require_matching_permissive_bytes_at_source_path(self):
        prepare = module("prepare")
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            license_bytes = b"Permission is hereby granted, free of charge; the above copyright notice."
            license_sha = hashlib.sha256(license_bytes).hexdigest()
            source = {"repo": "owner/project", "commit": "a" * 40, "parent": "b" * 40,
                      "path": "package/module.py", "code_license": "MIT", "advisory_ids": ["GHSA-example"]}
            item = {"key": "example", "repo": source["repo"], "commit": source["commit"],
                    "parent": source["parent"], "source_path": source["path"], "license": "MIT",
                    "license_file": "LICENSE", "advisory_ids": source["advisory_ids"],
                    "checked": ["commit_parent", "vulnerable_and_fixed_function_blobs",
                                "license_and_notice_files_at_commit", "package_metadata_at_commit"],
                    "metadata": [],
                    "notices": [{"path": "LICENSE", "sha256": license_sha, "classified_as": "MIT"}]}
            report = {"schema": "haven-secpatch-fix-source-check-v1", "requested": 1, "checked": 1,
                      "failures": [], "items": [item],
                      "notice_texts": {license_sha: base64.b64encode(license_bytes).decode()}}
            check = root / "source-check.json"
            check.write_text(json.dumps(report))
            used = {"example": {"source": source}}
            harvest = {"example": {"license_file": "LICENSE"}}
            prepare.write_source_notices(root / "good", check, used, harvest)
            self.assertEqual((root / "good" / "notices" / (license_sha + ".txt")).read_bytes(), license_bytes)
            gpl = b"GNU General Public License version 3"
            gpl_sha = hashlib.sha256(gpl).hexdigest()
            item["notices"].append({"path": "package/LICENSE", "sha256": gpl_sha, "classified_as": "MIT"})
            report["notice_texts"][gpl_sha] = base64.b64encode(gpl).decode()
            check.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "Non-permissive"):
                prepare.write_source_notices(root / "bad", check, used, harvest)

    def test_package_metadata_rejects_restrictive_license_despite_root_notice(self):
        metadata = module("license_metadata")
        for value in ("GPL-3.0-or-later", "FSL-1.0-Apache-2.0", "ZPL 2.1", "AGPL"):
            raw = ('[project]\nlicense = "' + value + '"\n').encode()
            item = {"key": "example", "notices": [{"path": "LICENSE"}],
                    "metadata": [{"path": "package/pyproject.toml", "sha256": "content"}]}
            with self.assertRaisesRegex(ValueError, "outside campaign allowlist"):
                metadata.validate_metadata(item, {"content": raw})
        self.assertTrue(metadata.allowed_declaration("MIT OR Apache-2.0"))

    def test_deeper_source_license_overrides_broader_package_metadata(self):
        metadata = module("license_metadata")
        item = {"key": "example", "notices": [{"path": "LICENSE"}, {"path": "applications/admin/LICENSE"}],
                "metadata": [{"path": "pyproject.toml", "sha256": "content"}]}
        result = metadata.validate_metadata(item, {"content": b'[project]\nlicense="GPL-3.0-or-later"\n'})
        self.assertEqual(result["precedence"], "deeper_source_license")

    def test_pipeline_files_match_recorded_base_and_preserve_upstream(self):
        base = json.loads((REMOTE / "SOURCE_BASE.json").read_text())
        self.assertEqual(base["upstream_base"]["base_commit"], "eaa76f834bc9f64fe9aada542fdf3c00ba9a6f55")
        self.assertEqual(set(base["upstream_base"]["core_sha256"]), set(base["core_sha256"]))
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
