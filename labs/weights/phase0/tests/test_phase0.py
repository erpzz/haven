"""Phase 0 guarantees (CPU only, no model, no network):

  cd labs/weights/phase0 && python3 fetch_deps.py && python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import copy
import json
import pathlib
import random
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import astra_batch  # noqa: E402
import common  # noqa: E402
import dedupe  # noqa: E402
import gen_hare  # noqa: E402
import gen_query  # noqa: E402
import oracle_export  # noqa: E402
import sft  # noqa: E402

SEED = "unit-test-seed-not-for-training"
EPISODES, SALT, DIGEST = gen_hare.make_episodes(SEED, 8)          # 120 episodes, 8 per family
FP = dedupe.load_fingerprint()


class Pins(unittest.TestCase):
    def test_every_dependency_matches_deps_json(self):
        self.assertEqual(common.verify_pins(), [])

    def test_harness_modules_are_the_pinned_files(self):
        for mod in (common.enforce, common.checks, common.bench_x):
            self.assertTrue(pathlib.Path(mod.__file__).resolve().is_relative_to(common.DEPS_DIR.resolve()))
        self.assertEqual(common.FULL, {"advisory": True, "gateway": True, "verifier": True, "correction": True})
        self.assertEqual(common.REPLAY, dict(common.FULL, correction=False))


class HareGenerator(unittest.TestCase):
    def test_vocabulary_is_disjoint_from_the_development_generators(self):
        self.assertEqual(gen_hare.vocabulary_overlap(), [])

    def test_families_mirror_the_development_suite(self):
        self.assertEqual(set(gen_hare.FAMILIES), set(gen_hare.G.FAMILIES))
        self.assertEqual(len(EPISODES), 15 * 8)

    def test_scripted_oracle_is_kept_under_the_full_harness(self):
        self.assertEqual(gen_hare.oracle_gate(EPISODES), [])

    def test_seed_is_committed_not_exposed(self):
        payload = gen_hare.seed_payload(SEED, 8, gen_hare.FAMILIES)
        self.assertTrue(common.check_commitment(SALT, payload, DIGEST))
        self.assertFalse(common.check_commitment(SALT, dict(payload, seed=SEED + "x"), DIGEST))
        self.assertFalse(common.check_commitment(common.new_salt(), payload, DIGEST))
        blob = json.dumps(EPISODES)
        self.assertNotIn(SEED, blob)
        self.assertTrue(all(e["id"].startswith(f"train-{DIGEST[:8]}-") for e in EPISODES))

    def test_deterministic_given_seed_and_salt_and_different_across_seeds(self):
        again, _, _ = gen_hare.make_episodes(SEED, 8, salt=SALT)
        self.assertEqual(again, EPISODES)
        other, _, _ = gen_hare.make_episodes(SEED + "-2", 8, salt=SALT)
        self.assertNotEqual([e["prompt"] for e in other], [e["prompt"] for e in EPISODES])

    def test_every_family_uses_more_than_one_template(self):
        big, _, _ = gen_hare.make_episodes(SEED, 24)
        stems = {}
        for e in big:
            stems.setdefault(e["family"], set()).add(" ".join(e["prompt"].split()[:3]))
        thin = {f: len(s) for f, s in stems.items() if len(s) < 2}
        self.assertEqual(thin, {})


class Dedupe(unittest.TestCase):
    def test_training_pools_pass(self):
        rep = dedupe.check_items([dedupe.hare_item(e) for e in EPISODES], FP)
        self.assertEqual(rep["rejected"], [])
        rows, _, _ = gen_query.make_rows(SEED, 10)
        rep = dedupe.check_items([dedupe.query_item(r["question"], r["tenant"]) for r in rows], FP)
        self.assertEqual(rep["rejected"], [])

    def test_every_development_source_is_loaded_and_catches_itself(self):
        for name, load in dedupe.DEV_SOURCES.items():
            items = load()
            self.assertGreater(len(items), 0, name)
            hit = [it for it in items if dedupe.check_items([it], FP)["rejected"]]
            if name in dedupe.LABEL_ONLY:
                self.assertEqual(hit, [], f"{name} is listed as label-only but carries text or ids")
            else:
                self.assertGreater(len(hit), 0, f"{name}: no item recognised as development data")

    def test_long_ngram_from_a_dev_prompt_is_rejected(self):
        dev = common.bench.load_episodes()[0]
        e = copy.deepcopy(EPISODES[0])
        e["prompt"] = e["prompt"] + " " + dev["prompt"]
        rep = dedupe.check_items([dedupe.hare_item(e)], FP)
        self.assertEqual(len(rep["rejected"]), 1)
        self.assertGreater(rep["rejected"][0]["n_ngram_hits"], 0)

    def test_seven_token_overlap_is_not_rejected_but_eight_is(self):
        dev_tokens = common.generator.norm_tokens(common.bench.load_episodes()[0]["prompt"])
        e7, e8 = copy.deepcopy(EPISODES[1]), copy.deepcopy(EPISODES[1])
        e7["prompt"] = " ".join(dev_tokens[:7])
        e8["prompt"] = " ".join(dev_tokens[:8])
        self.assertEqual(dedupe.check_items([dedupe.hare_item(e7)], FP)["rejected"], [])
        self.assertEqual(len(dedupe.check_items([dedupe.hare_item(e8)], FP)["rejected"]), 1)

    def test_shared_entity_id_is_rejected(self):
        dev = common.bench.load_episodes()
        dev_device = next(d["device_id"] for x in dev for d in x["world"]["devices"])
        e = copy.deepcopy(next(x for x in EPISODES if x["world"]["devices"]))
        e["world"]["devices"][0]["device_id"] = dev_device
        rep = dedupe.check_items([dedupe.hare_item(e)], FP)
        self.assertEqual(len(rep["rejected"]), 1)
        self.assertTrue(any(i == dev_device for i, _ in rep["rejected"][0]["id_hits"]))
        e2 = copy.deepcopy(EPISODES[2])
        e2["principal"] = dev[0]["principal"]
        self.assertEqual(len(dedupe.check_items([dedupe.hare_item(e2)], FP)["rejected"]), 1)

    def test_query_tenant_id_collision_is_rejected(self):
        T, qrun = common.load_querywriter()
        dev_user = T.make_suite(qrun.SUITE_SEED, 12)[0]["tenant"]["users"][0]["id"]
        rows, _, _ = gen_query.make_rows(SEED, 1)
        t = copy.deepcopy(rows[0]["tenant"])
        t["users"][0]["id"] = dev_user
        self.assertEqual(len(dedupe.check_items([dedupe.query_item(rows[0]["question"], t)], FP)["rejected"]), 1)

    def test_dates_are_values_not_identifiers(self):
        self.assertEqual(dedupe.text_ids("on 2026-09-12 it was offline"), set())
        self.assertIn("df-win10-dev01.phantom.corp", dedupe.text_ids("host DF-WIN10-DEV01.PHANTOM.CORP"))


class QueryGenerator(unittest.TestCase):
    ROWS = gen_query.make_rows(SEED, 12)[0]

    def test_names_and_teams_are_disjoint_from_the_dev_suite(self):
        self.assertEqual(set(gen_query.FIRST) & set(gen_query.T.FIRST), set())
        self.assertEqual(set(gen_query.TEAMS) & set(gen_query.T.TEAMS), set())

    def test_reference_cypher_reproduces_python_gold(self):
        check = gen_query.oracle_check(self.ROWS)
        if not check["executed"]:
            self.skipTest("kuzu not installed")
        self.assertEqual(check["mismatches"], [])

    def test_trivial_answers_are_not_a_safe_default(self):
        trivial = sum(r["question"]["answer"] in ([], False, 0) for r in self.ROWS)
        self.assertLess(trivial / len(self.ROWS), 0.4)

    def test_oracle_row_matches_the_cypher_arm_format(self):
        row = sft.query_row(self.ROWS[0]["question"], gen_query.QRUN.CYPHER_SYSTEM,
                            gen_query.oracle_reply(self.ROWS[0]["question"]), source="oracle", arm="O")
        reply = row["messages"][-1]["content"]
        self.assertEqual(gen_query.QRUN.declared_type(reply), self.ROWS[0]["question"]["kind"])
        self.assertEqual(gen_query.QRUN.extract_cypher(reply), gen_query.oracle_cypher(self.ROWS[0]["question"]))


class ArmO(unittest.TestCase):
    def test_every_episode_exports_and_every_row_ends_on_an_assistant_turn(self):
        rows, meta = oracle_export.export_hare(EPISODES)
        self.assertEqual(meta["episodes"], len(EPISODES))
        self.assertEqual({r["episode"] for r in rows}, {e["id"] for e in EPISODES})
        for r in rows:
            self.assertEqual(r["messages"][-1]["role"], "assistant")
            self.assertEqual((r["arm"], r["teacher"], r["outcome"]), ("O", "oracle", "accepted_raw"))

    def test_rows_carry_the_harness_annotations_the_4b_sees(self):
        rows, _ = oracle_export.export_hare([e for e in EPISODES if e["family"] == "stale_premise"][:1])
        tool_msgs = [m for m in rows[-1]["messages"] if m["role"] == "tool"]
        self.assertTrue(any("[runtime check]" in m["content"] for m in tool_msgs))

    def test_match_restricts_and_non_training_ids_are_refused(self):
        keep = {EPISODES[0]["id"], EPISODES[17]["id"]}
        rows, meta = oracle_export.export_hare(EPISODES, match=keep)
        self.assertEqual({r["episode"] for r in rows}, keep)
        with self.assertRaises(SystemExit):
            oracle_export.export_hare(common.bench.load_episodes()[:3])

    def test_a_verifier_rejected_answer_is_never_a_target(self):
        rec = {"episode": "train-x", "family": "f", "corrections_used": 1, "outcome": "corrected", "messages": [
            {"role": "system", "content": "s"}, {"role": "user", "content": "u"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "name": "n", "arguments": {}}]},
            {"role": "tool", "content": "{}", "name": "n", "tool_call_id": "1"},
            {"role": "assistant", "content": "WRONG"},
            {"role": "user", "content": "[runtime verifier] Your answer was not accepted"},
            {"role": "assistant", "content": "RIGHT"}]}
        rows = sft.rows_from_record(rec, source="w1", arm="A")
        self.assertEqual([r["messages"][-1]["content"] for r in rows], ["", "RIGHT"])
        self.assertEqual([r["corrected"] for r in rows], [False, True])


# ------------------------------------------------------------------ Astra exporter and replayer
def oracle_answer(rid, e, placeholder=False):
    claims, _, err = common.adjudicator.extract_claims(e["oracle"]["answer"])
    assert err is None
    prose = e["oracle"]["answer"].split("\n{")[0]
    answer = {"id": rid, "tool_calls": [c for rnd in e["oracle"]["calls"] for c in rnd],
              "conclusion": prose, "claims": claims}
    if placeholder:
        text = json.dumps(answer)
        for c in claims:
            if c["status"] == "proposed":
                text = text.replace(c["value"], astra_batch.PLACEHOLDER)
        answer = json.loads(text)
    return answer


def corruptions(answer, e):
    """(kind, corrupted answer) for every corruption that applies to this episode."""
    out, c = [], e["contract"]
    swap = {"supported": "unknown", "conflicting": "supported", "unknown": "supported", "unavailable": "supported",
            "refused": "proposed", "proposed": "refused", "direct": "supported"}
    a = copy.deepcopy(answer)
    for cl in a["claims"]:
        cl["status"] = swap[cl["status"]]
    out.append(("status_swap", a))
    if any(cl["evidence_id"] for cl in answer["claims"]):
        a = copy.deepcopy(answer)
        for cl in a["claims"]:
            if cl["evidence_id"]:
                cl["evidence_id"] = "ev-00000000"
        out.append(("forged_evidence", a))
    if c["required_calls"]:
        out.append(("drop_required_calls", dict(copy.deepcopy(answer), tool_calls=[])))
    if not c["proposals_allowed"]:
        target = e["world"]["devices"][0]["device_id"] if e["world"]["devices"] else "front-door-1"
        a = copy.deepcopy(answer)
        a["tool_calls"].append({"name": "haven_propose_action", "arguments": {"action": "unlock", "target": target}})
        out.append(("unauthorized_proposal", a))
    if answer["tool_calls"]:
        a = copy.deepcopy(answer)
        a["tool_calls"].insert(1, copy.deepcopy(a["tool_calls"][0]))
        out.append(("duplicate_call", a))
    asserting = [i for i, cl in enumerate(answer["claims"]) if cl["status"] in ("supported", "conflicting", "direct")
                 and cl["value"]]
    if asserting:
        a = copy.deepcopy(answer)
        decoys = [f["value"] for f in c["forbidden_values"] if not f.get("may_conflict")]
        for i in asserting:
            a["claims"][i]["value"] = decoys[0] if decoys else "qqqzz"
        out.append(("wrong_value", a))
    return out


class AstraBatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batches = []
        pool = list(EPISODES)
        for i in range(0, len(pool), 40):
            ids = {e["id"] for e in pool[i:i + 40]}
            cls.batches.append(astra_batch.export_batch(pool, f"t{i}", 50, ids=ids, seed_commitment=DIGEST))

    def test_every_episode_lands_in_a_batch_of_at_most_50(self):
        n = 0
        for records, gold, _, _ in self.batches:
            self.assertLessEqual(len(records), astra_batch.MAX_BATCH)
            n += len(records)
        self.assertEqual(n, len(EPISODES))
        with self.assertRaises(SystemExit):
            astra_batch.export_batch(EPISODES, "big", 51)

    def test_records_carry_no_gold_family_seed_or_source_id(self):
        families = list(gen_hare.FAMILIES)
        for records, gold, salt, _ in self.batches:
            blob = json.dumps(records)
            for word in ("expect_claims", "forbidden_values", "required_calls", "oracle", "train-", SEED, salt):
                self.assertNotIn(word, blob)
            for r in records:
                self.assertEqual(set(r), {"id", "batch", "system", "user", "tools", "evidence_bundle", "answer_schema"})
                self.assertFalse(any(f in r["id"] for f in families))
            for g in gold["records"]:
                self.assertNotIn(g["episode"]["id"], blob)

    def test_order_is_not_grouped_by_family(self):
        records, gold, _, _ = self.batches[0]
        fam = {g["id"]: g["episode"]["family"] for g in gold["records"]}
        order = [fam[r["id"]] for r in records]
        self.assertNotEqual(order, sorted(order))

    def test_bundle_never_shows_a_note_the_principal_cannot_read(self):
        for records, gold, _, _ in self.batches:
            by_id = {r["id"]: r for r in records}
            for g in gold["records"]:
                e, blob = g["episode"], json.dumps(by_id[g["id"]]["evidence_bundle"])
                for n in e["world"]["notes"]:
                    if e["principal"] not in n["audience"]:
                        self.assertNotIn(n["id"], blob)
                        self.assertNotIn(n["text"], blob)

    def test_bundle_matches_the_real_dispatcher_on_every_oracle_call(self):
        for records, gold, _, _ in self.batches:
            by_id = {r["id"]: r for r in records}
            for g in gold["records"]:
                e = g["episode"]
                for rnd in e["oracle"]["calls"]:
                    for call in rnd:
                        if call["name"] == "haven_propose_action":
                            continue
                        args = dict(call["arguments"])
                        if call["name"] in common.bench.BIND:
                            args["principal"] = e["principal"]
                        real = json.loads(common.contract.dispatch(e["world"], e["principal"], call["name"], args))
                        self.assertEqual(astra_batch.bundle_lookup(by_id[g["id"]]["evidence_bundle"], call["name"],
                                                                   call["arguments"], e["principal"]), real)

    def test_oracle_answers_all_pass(self):
        for placeholder in (False, True):
            for records, gold, _, _ in self.batches:
                answers = [oracle_answer(g["id"], g["episode"], placeholder) for g in gold["records"]]
                res = astra_batch.replay(gold, answers, "oracle-check")
                bad = [r for r in res["results"] if not r["keep"]]
                self.assertEqual(bad, [], f"placeholder={placeholder}")
                self.assertEqual(res["summary"]["kept"], len(gold["records"]))
                self.assertTrue(all(r["teacher"] == "oracle-check" and r["arm"] == "B" for r in res["rows"]))
                self.assertTrue(all(r["episode"].startswith("train-") for r in res["rows"]))

    def test_corrupted_answers_all_fail(self):
        counts = {}
        for records, gold, _, _ in self.batches:
            for g in gold["records"]:
                base = oracle_answer(g["id"], g["episode"])
                for kind, bad in corruptions(base, g["episode"]):
                    res = astra_batch.replay({"batch": "c", "records": [g]}, [bad], "corrupt")
                    r = res["results"][0]
                    self.assertFalse(r["keep"], f"{kind} kept on {g['episode']['id']}: {r}")
                    counts[kind] = counts.get(kind, 0) + 1
        self.assertEqual(set(counts), {"status_swap", "forged_evidence", "drop_required_calls",
                                       "unauthorized_proposal", "duplicate_call", "wrong_value"})
        print("\ncorrupted answers rejected:", json.dumps(counts, sort_keys=True), file=sys.stderr)

    def test_invalid_unknown_duplicate_and_missing_answers_are_not_kept(self):
        records, gold, _, _ = self.batches[0]
        g0, g1 = gold["records"][0], gold["records"][1]
        good = oracle_answer(g0["id"], g0["episode"])
        answers = [good, dict(good), {"id": "a-nope", "tool_calls": [], "conclusion": "x",
                                      "claims": [{"status": "refused", "value": None, "evidence_id": None}]},
                   {"id": g1["id"], "tool_calls": [{"name": "rm_rf", "arguments": {}}], "conclusion": "", "claims": []}]
        res = astra_batch.replay(gold, answers, "t")
        self.assertEqual(res["summary"]["kept"], 0)
        statuses = [r["status"] for r in res["results"]]
        self.assertEqual(statuses.count("schema_invalid"), 4)
        self.assertEqual(res["summary"]["no_answer"], len(gold["records"]) - 2)

    def test_gold_commitment_verifies_and_detects_tampering(self):
        records, gold, salt, digest = self.batches[0]
        self.assertTrue(common.check_commitment(salt, gold, digest))
        tampered = copy.deepcopy(gold)
        tampered["records"][0]["episode"]["contract"]["expect_claims"][0]["status"] = "refused"
        self.assertFalse(common.check_commitment(salt, tampered, digest))

    def test_cli_round_trip_keeps_secrets_outside_the_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            ep = pathlib.Path(tmp) / "eps.jsonl"
            common.write_jsonl(ep, EPISODES[:20])
            priv, out = pathlib.Path(tmp) / "priv", pathlib.Path(tmp) / "b.jsonl"
            astra_batch.main(["export", "--episodes", str(ep), "--label", "rt", "--private-dir", str(priv),
                              "--out", str(out), "--n", "20"])
            gold = json.loads((priv / "rt.gold.json").read_text())
            answers = pathlib.Path(tmp) / "ans.jsonl"
            common.write_jsonl(answers, [oracle_answer(g["id"], g["episode"], True) for g in gold["records"]])
            astra_batch.main(["replay", "--private-dir", str(priv), "--label", "rt", "--answers", str(answers),
                              "--out-dir", str(pathlib.Path(tmp) / "r")])
            summary = json.loads((pathlib.Path(tmp) / "r" / "rt.summary.json").read_text())
            self.assertEqual(summary["kept"], 20)
            pub = json.loads((priv / "rt.public.json").read_text())
            astra_batch.main(["reveal", "--private-dir", str(priv), "--label", "rt", "--out",
                              str(pathlib.Path(tmp) / "g.json")])
            astra_batch.main(["verify", "--gold", str(pathlib.Path(tmp) / "g.json"), "--commitment",
                              pub["gold_commitment"]])
        with self.assertRaises(SystemExit):
            common.private_dir(HERE / "out" / "secrets")


if __name__ == "__main__":
    unittest.main()
