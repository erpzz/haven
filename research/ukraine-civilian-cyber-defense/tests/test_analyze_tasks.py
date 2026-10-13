import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyze_tasks import analyze_export, analyze_task


class TriageTests(unittest.TestCase):
    def test_published_task_pattern(self):
        task = {"TaskName": "GoogleUpdateTaskMachineUA{sample}", "TaskPath": "\\", "Actions": []}
        result = analyze_task(task)
        self.assertEqual(result["priority"], "review")
        self.assertIn("published DSLU", " ".join(result["reasons"]))

    def test_high_priority_script_in_public_music(self):
        task = {"TaskName": "IndependentName", "Actions": [
            {"Execute": "C:\\Windows\\System32\\wscript.exe", "Arguments": '"C:\\Users\\Public\\Music\\apple.vbe"'}]}
        result = analyze_task(task)
        self.assertEqual(result["priority"], "high")
        self.assertGreaterEqual(result["score"], 4)

    def test_normal_google_update_not_flagged(self):
        task = {"TaskName": "GoogleUpdateTaskMachineCore", "Actions": [
            {"Execute": "C:\\Program Files (x86)\\Google\\Update\\GoogleUpdate.exe", "Arguments": "/c"}]}
        self.assertIsNone(analyze_task(task))

    def test_does_not_flag_generic_script_host(self):
        task = {"TaskName": "CustomBackup", "Actions": [
            {"Execute": "cscript.exe", "Arguments": "C:\\approved\\backup.vbs"}]}
        self.assertIsNone(analyze_task(task))

    def test_powershell_encoded_command(self):
        task = {"TaskName": "unknown", "Actions": [
            {"Execute": "powershell.exe", "Arguments": "-EncodedCommand XXX -WindowStyle Hidden"}]}
        result = analyze_task(task)
        self.assertEqual(result["score"], 3)

    def test_single_task_export_supported(self):
        findings = analyze_export({"TaskName": "GoogleUpdateTaskMachineUA{123}", "Actions": []})
        self.assertEqual(len(findings), 1)

    def test_non_object_rejected(self):
        with self.assertRaises(ValueError):
            analyze_export(["bad"])

    def test_priority_sorting(self):
        a = {"TaskName": "GoogleUpdateTaskMachineUA{123}", "Actions": []}
        b = {"TaskName": "Another", "Actions": [
            {"Execute": "wscript", "Arguments": "C:\\Users\\Public\\Music\\apple.vbe"}]}
        results = analyze_export([a, b])
        self.assertEqual(results[0]["task_name"], "Another")


if __name__ == "__main__":
    unittest.main()
