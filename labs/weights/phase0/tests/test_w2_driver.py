import importlib.util
import json
from pathlib import Path

DRIVER = Path(__file__).resolve().parents[1] / "w2_driver.py"
SPEC = importlib.util.spec_from_file_location("w2_driver", DRIVER)
w2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(w2)


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_counts_and_open_ids():
    session = {
        "a": {"calls": [], "final": None, "rejected": None},
        "b": {"calls": [], "final": {"x": 1}, "rejected": None},
        "c": {"calls": [], "final": None, "rejected": "bad"},
    }
    assert w2.counts(session) == {"assigned": 3, "final": 1, "rejected": 1, "open": 1}
    assert w2.open_ids(session) == {"a"}


def test_validate_reply_requires_exact_open_set_and_round(tmp_path):
    session = {
        "a": {"calls": [{"name": "x", "arguments": {}}], "final": None, "rejected": None},
        "b": {"calls": [], "final": {"x": 1}, "rejected": None},
    }
    p = tmp_path / "b.reply1.jsonl"
    write_jsonl(p, [{
        "schema": w2.SCHEMA,
        "batch": "b",
        "id": "a",
        "round": 1,
        "action": "call",
        "call": {"name": "haven_device_state", "arguments": {"device_id": "d"}},
    }])
    assert len(w2.validate_reply(p, "b", session)) == 1


def test_validate_reply_rejects_wrong_round(tmp_path):
    session = {"a": {"calls": [], "final": None, "rejected": None}}
    p = tmp_path / "b.reply0.jsonl"
    write_jsonl(p, [{
        "schema": w2.SCHEMA,
        "batch": "b",
        "id": "a",
        "round": 1,
        "action": "call",
        "call": {"name": "x", "arguments": {}},
    }])
    try:
        w2.validate_reply(p, "b", session)
    except w2.DriverError as exc:
        assert "expected 0" in str(exc)
    else:
        raise AssertionError("wrong round accepted")
