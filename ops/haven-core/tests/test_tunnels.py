"""Supervised reverse tunnels for the Mac worker and cloud lanes: offline checks, no ssh or launchctl is run."""
import importlib.util
import os
import pathlib
import plistlib
import socket
import subprocess
import tempfile
import types
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mac = load("mac_worker", "mac-worker.py")
cloud = load("cloud_worker", "cloud-worker.py")


class Calls:
    """Records argv; answers ssh -O check and launchctl print from a scripted state."""

    def __init__(self, alive=False, loaded=False):
        self.argv, self.alive, self.loaded = [], alive, loaded

    def __call__(self, *argv, check=True, **kwargs):
        argv = list(argv[0]) if len(argv) == 1 and isinstance(argv[0], list) else list(argv)
        self.argv.append(argv)
        code, out = 0, ""
        if "-O" in argv and argv[argv.index("-O") + 1] == "check":
            code = 0 if self.alive else 255
        elif "-O" in argv and argv[argv.index("-O") + 1] == "exit":
            self.alive = False
        elif argv[:2] == ["launchctl", "print"]:
            code = 0 if self.loaded else 113
        elif argv[:2] == ["launchctl", "bootstrap"]:
            self.loaded = True
        elif argv[:2] == ["launchctl", "bootout"]:
            self.loaded = False
        elif argv and argv[0] == "/usr/sbin/sysctl":
            out = "17179869184\n"
        elif argv and argv[0] == "ssh" and "python3 -c" in argv[-1]:
            out = "/home/slinky/.local/share/haven-model-lab/providers" + (
                "/macbook-owner.sock" if "macbook-owner" in argv[-1] else "") + "\n"
        return types.SimpleNamespace(returncode=code, stdout=out, stderr="")

    def find(self, pred):
        return [a for a in self.argv if pred(a)]


class MacTunnelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        home = pathlib.Path(self.tmp.name)
        self.patches = [mock.patch.object(mac, "SOCKET", home / "w.sock"),
                        mock.patch.object(mac, "STATE", home / "state"),
                        mock.patch.object(mac, "TUNNEL_PLIST", home / "LaunchAgents/t.plist"),
                        mock.patch.object(mac, "prepare", lambda: None)]
        for p in self.patches:
            p.start()
        (home / "state").mkdir()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_foreground_tunnel_clears_dead_sockets_then_execs_ssh(self):
        calls = Calls(alive=False)
        dead = socket.socket(socket.AF_UNIX)
        dead.bind(str(mac.SOCKET))
        dead.close()  # a socket file with nothing listening, as a dead master leaves it
        with mock.patch.object(mac, "run", calls), mock.patch.object(mac.os, "execvp") as execvp:
            mac.tunnel()
        self.assertFalse(os.path.lexists(mac.SOCKET))
        prep = calls.find(lambda a: a[0] == "ssh" and "python3 -c" in a[-1])
        self.assertTrue(prep[0][-1].endswith(" clear"))  # remote dead-socket clear runs before binding
        argv = execvp.call_args[0][1]
        self.assertIn("-NT", argv)
        self.assertNotIn("-fNT", argv)  # launchd must see ssh exit
        self.assertIn("ExitOnForwardFailure=yes", argv)
        self.assertEqual(argv[argv.index("-R") + 1],
                         "/home/slinky/.local/share/haven-model-lab/providers/macbook-owner.sock:127.0.0.1:8890")

    def test_foreground_tunnel_leaves_a_live_hand_started_tunnel(self):
        calls = Calls(alive=True)
        with mock.patch.object(mac, "run", calls), mock.patch.object(mac.os, "execvp") as execvp, \
                mock.patch.object(mac.time, "sleep") as sleep:
            mac.tunnel()
        execvp.assert_not_called()
        sleep.assert_called_once()
        self.assertFalse(calls.find(lambda a: "clear" in a[-1]))

    def test_local_path_that_is_not_our_socket_is_refused(self):
        mac.SOCKET.write_text("not a socket")
        with mock.patch.object(mac, "run", Calls()), mock.patch.object(mac.os, "execvp") as execvp:
            with self.assertRaises(ValueError):
                mac.tunnel()
        execvp.assert_not_called()
        self.assertTrue(mac.SOCKET.exists())

    def test_enable_tunnel_hands_over_and_installs_keepalive_agent(self):
        calls = Calls(alive=True)
        with mock.patch.object(mac, "run", calls), mock.patch.object(mac.Path, "home", lambda: pathlib.Path(self.tmp.name)):
            mac.enable_tunnel()
        plist = plistlib.loads(mac.TUNNEL_PLIST.read_bytes())
        self.assertEqual(plist["Label"], mac.TUNNEL_LABEL)
        self.assertIs(plist["KeepAlive"], True)
        self.assertEqual(plist["ProgramArguments"][-1], "tunnel")
        self.assertGreaterEqual(plist["ThrottleInterval"], 30)
        self.assertTrue(calls.find(lambda a: "-O" in a and a[a.index("-O") + 1] == "exit"))
        self.assertTrue(calls.loaded)

    def test_enroll_with_supervisor_starts_no_second_tunnel(self):
        calls = Calls(alive=False, loaded=True)
        with mock.patch.object(mac, "run", calls), \
                mock.patch.object(mac, "STATE", pathlib.Path(self.tmp.name) / "state"):
            (mac.STATE / "node-id").write_text("n\n")
            (mac.STATE / "api-key").write_text("k\n")
            mac.enroll()
        self.assertFalse(calls.find(lambda a: "-fNT" in a or "-NT" in a))
        self.assertFalse(calls.find(lambda a: a[-1].endswith(" clear")))  # the supervisor owns the clear

    def test_disable_unloads_supervisor_before_closing_tunnel(self):
        calls = Calls(alive=True, loaded=False)
        with mock.patch.object(mac, "run", calls):
            mac.disable()
        flat = [" ".join(a) for a in calls.argv]
        boot = next(i for i, a in enumerate(flat) if "bootout" in a and mac.TUNNEL_LABEL in a)
        exit_ = next(i for i, a in enumerate(flat) if "-O exit" in a)
        self.assertLess(boot, exit_)


class CloudTunnelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        home = pathlib.Path(self.tmp.name)
        self.patches = [mock.patch.object(cloud, "SOCKET", home / "c.sock"),
                        mock.patch.object(cloud, "STATE", home / "state"),
                        mock.patch.object(cloud, "TUNNEL_PLIST", home / "LaunchAgents/t.plist"),
                        mock.patch.object(cloud, "prepare",
                                          lambda: {"lanes": ["haven-claude-code", "haven-codex-cli"], "daily_cap": 50})]
        for p in self.patches:
            p.start()
        (home / "state").mkdir()
        self.args = types.SimpleNamespace(data_dir="~/.local/share/haven-model-lab", lab_dir="")

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def patched(self, calls):
        return [mock.patch.object(cloud.subprocess, "run", calls),
                mock.patch.object(cloud, "launchctl", lambda *a, check=True: calls(["launchctl", *a]))]

    def test_foreground_tunnel_forwards_every_lane_and_clears_only_them(self):
        calls = Calls(alive=False)
        with self.patched(calls)[0], self.patched(calls)[1], mock.patch.object(cloud.os, "execvp") as execvp:
            cloud.tunnel(self.args)
        prep = calls.find(lambda a: a[0] == "ssh" and "python3 -c" in a[-1])[0][-1]
        self.assertTrue(prep.endswith("cloud-claude-code cloud-codex-cli"))
        argv = execvp.call_args[0][1]
        self.assertIn("-NT", argv)
        forwards = [argv[i + 1] for i, a in enumerate(argv) if a == "-R"]
        self.assertEqual([f.split("/")[-1] for f in forwards],
                         ["cloud-claude-code.sock:127.0.0.1:8891", "cloud-codex-cli.sock:127.0.0.1:8891"])

    def test_enroll_with_supervisor_restarts_it_and_starts_no_tunnel(self):
        calls = Calls(alive=False, loaded=True)
        (cloud.STATE / "node-id").write_text("n\n")
        (cloud.STATE / "api-key").write_text("k\n")
        with self.patched(calls)[0], self.patched(calls)[1]:
            cloud.enroll(self.args)
        self.assertFalse(calls.find(lambda a: "-fNT" in a))
        prep = calls.find(lambda a: a[0] == "ssh" and "python3 -c" in a[-1])[0][-1]
        self.assertFalse(prep.endswith("cloud-codex-cli"))  # no clearing while the supervisor may be serving
        self.assertTrue(calls.find(lambda a: a[:2] == ["launchctl", "kickstart"] and cloud.TUNNEL_LABEL in a[-1]))

    def test_disable_unloads_supervisor(self):
        calls = Calls(alive=True, loaded=True)
        with self.patched(calls)[0], self.patched(calls)[1]:
            cloud.disable()
        flat = [" ".join(a) for a in calls.argv]
        boot = next(i for i, a in enumerate(flat) if "bootout" in a and cloud.TUNNEL_LABEL in a)
        exit_ = next(i for i, a in enumerate(flat) if "-O exit" in a)
        self.assertLess(boot, exit_)


if __name__ == "__main__":
    unittest.main()
