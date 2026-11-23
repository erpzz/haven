"""Phase 0 guarantees (CPU only, no model, no network):

  cd labs/weights/phase0 && python3 fetch_deps.py && python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import collections
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


# ------------------------------------------------------------------ Astra stepwise exchange
import pools  # noqa: E402

DISP = {"answer": "answer", "insufficient_evidence": "insufficient_evidence", "no_action_needed": "no_action_needed",
        "refusal": "refusal"}


def oracle_plan(e, placeholder=False):
    claims, _, err = common.adjudicator.extract_claims(e["oracle"]["answer"])
    assert err is None
    calls = [c for rnd in e["oracle"]["calls"] for c in rnd]
    if placeholder:
        claims = [dict(c, value=astra_batch.PLACEHOLDER, evidence_id=astra_batch.PLACEHOLDER)
                  if c["status"] == "proposed" else c for c in claims]
    final = {"tool_calls": calls, "disposition": pools.disposition(e), "conclusion": e["oracle"]["answer"].split("\n{")[0],
             "claims": claims}
    return calls, final


def run_session(gold, session, plans, label, mutate_reply=None):
    """Drive a stepwise session: each id sends its planned calls one per round, then its final record."""
    for rnd in range(astra_batch.MAX_CALLS + 2):
        replies = []
        for rid, s in session.items():
            if s["final"] is not None or s["rejected"]:
                continue
            calls, final = plans[rid]
            if len(s["calls"]) < len(calls):
                r = {"schema": astra_batch.SCHEMA, "batch": label, "id": rid, "round": len(s["calls"]),
                     "action": "call", "call": calls[len(s["calls"])]}
            else:
                r = {"schema": astra_batch.SCHEMA, "batch": label, "id": rid, "action": "final", "final": final}
            replies.append(mutate_reply(rid, r) if mutate_reply else r)
        if not replies:
            break
        astra_batch.step(gold, session, replies)
    return astra_batch.seal_record(gold, session)


def corrupted_plans(e):
    """(kind, calls, final) for every corruption that applies to this episode; none may be kept."""
    calls, final = oracle_plan(e)
    c, out = e["contract"], []

    def f(**kw):
        return dict(copy.deepcopy(final), **kw)
    swap = {"supported": "unknown", "conflicting": "supported", "unknown": "supported", "unavailable": "supported",
            "refused": "proposed", "proposed": "refused", "direct": "supported"}
    sw = [dict(cl, status=swap[cl["status"]]) for cl in final["claims"]]
    sts = [x["status"] for x in sw]
    disp = "refusal" if "refused" in sts else ("insufficient_evidence" if all(x in ("unavailable", "unknown") for x in sts)
                                               else "answer")
    out.append(("status_swap", calls, f(claims=sw, disposition=disp)))
    if any(cl["evidence_id"] for cl in final["claims"]):
        out.append(("forged_evidence", calls, f(claims=[dict(cl, evidence_id="ev-00000000") if cl["evidence_id"] else cl
                                                        for cl in final["claims"]])))
    if c["required_calls"]:
        out.append(("drop_required_calls", [], f(tool_calls=[])))
    if not c["proposals_allowed"]:
        target = e["world"]["devices"][0]["device_id"] if e["world"]["devices"] else "front-door-1"
        extra = calls + [{"name": "haven_propose_action", "arguments": {"action": "unlock", "target": target}}]
        out.append(("unauthorized_proposal", extra, f(tool_calls=extra)))
    if calls:
        dup = calls[:1] + calls[:1] + calls[1:]
        out.append(("duplicate_call", dup, f(tool_calls=dup)))
    asserting = [i for i, cl in enumerate(final["claims"]) if cl["status"] in ("supported", "conflicting", "direct")
                 and cl["value"]]
    if asserting:
        decoys = [v["value"] for v in c["forbidden_values"] if not v.get("may_conflict")]
        wv = copy.deepcopy(final["claims"])
        for i in asserting:
            wv[i]["value"] = decoys[0] if decoys else "qqqzz"
        out.append(("wrong_value", calls, f(claims=wv)))
    # future citation: the conclusion and claims are correct, but the call that returns a cited record never ran
    cited = {cl["evidence_id"] for cl in final["claims"] if cl["evidence_id"]}
    for k in range(len(calls)):
        out_k = json.loads(common.contract.dispatch(e["world"], e["principal"], calls[k]["name"],
                                                    dict(calls[k]["arguments"], principal=e["principal"])))
        if cited & {out_k.get("evidence_id"), out_k.get("device_id")}:
            short = calls[:k] + calls[k + 1:]
            out.append(("future_citation", short, f(tool_calls=short)))
            break
    # future identifier: an id used before the call that reveals it
    if len(calls) >= 2 and calls[1]["name"] == "haven_device_state" and calls[1]["arguments"]["device_id"] not in e["prompt"]:
        rev = [calls[1], calls[0]] + calls[2:]
        out.append(("future_identifier", rev, f(tool_calls=rev)))
    out.append(("session_mismatch", calls, f(tool_calls=calls[:-1] if calls else [{"name": "haven_list_resources",
                                                                                    "arguments": {"kind": "devices"}}])))
    out.append(("clarification", calls, f(disposition="clarification")))
    out.append(("disposition_mismatch", calls, f(disposition="refusal" if final["disposition"] != "refusal" else "answer")))
    return out


class AstraStepwise(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batches = []
        for i in range(0, len(EPISODES), 40):
            ids = {e["id"] for e in EPISODES[i:i + 40]}
            cls.batches.append(astra_batch.export_batch(EPISODES, f"t{i}", 50, ids=ids, seed_commitment=DIGEST))

    def test_every_episode_lands_in_a_batch_of_at_most_50(self):
        self.assertEqual(sum(len(b[0]) for b in self.batches), len(EPISODES))
        with self.assertRaises(SystemExit):
            astra_batch.export_batch(EPISODES, "big", 51)

    def test_round0_reveals_no_tool_output_gold_family_seed_or_source_id(self):
        for records, gold, salt, _, _ in self.batches:
            blob = json.dumps(records)
            for word in ("expect_claims", "forbidden_values", "required_calls", "oracle", "train-", SEED, salt):
                self.assertNotIn(word, blob)
            for g in gold["records"]:
                e = g["episode"]
                self.assertNotIn(e["id"], blob)
                for n in e["world"]["notes"]:
                    self.assertNotIn(n["text"], blob)
                    self.assertNotIn(n["id"], blob)
                for d in e["world"]["devices"]:
                    if d["cause"] and len(d["cause"]) > 12:
                        self.assertNotIn(d["cause"], blob)
            for r in records:
                self.assertEqual(r["initial_observations"], [])
                self.assertFalse(any(f in r["id"] for f in gen_hare.FAMILIES))

    def test_round0_user_turn_is_exactly_what_the_4b_sees(self):
        records, gold, _, _, _ = self.batches[0]
        e = gold["records"][0]["episode"]
        rec = common.run_harness(common.Oracle(e), e, common.FULL)
        r = next(x for x in records if x["id"] == gold["records"][0]["id"])
        self.assertEqual((r["system"], r["user"]), (rec["messages"][0]["content"], rec["messages"][1]["content"]))

    def test_each_step_reveals_only_the_result_of_the_call_just_made(self):
        records, gold, _, _, _ = self.batches[0]
        g = gold["records"][0]
        e = g["episode"]
        calls, _ = oracle_plan(e)
        if not calls:
            g = next(x for x in gold["records"] if x["episode"]["oracle"]["calls"])
            e, (calls, _) = g["episode"], oracle_plan(g["episode"])
        session = {g["id"]: {"calls": [], "observations": [], "final": None, "rejected": None}}
        full = common.run_harness(common.Oracle(e), e, common.FULL)
        tool_msgs = [m["content"] for m in full["messages"] if m["role"] == "tool"]
        for k, call in enumerate(calls):
            obs, _ = astra_batch.step(gold, session, [{"schema": astra_batch.SCHEMA, "batch": gold["batch"],
                                                       "id": g["id"], "round": k, "action": "call", "call": call}])
            self.assertEqual(len(obs), 1)
            self.assertEqual(obs[0]["result"], tool_msgs[k])          # the annotated message the 4B would see
            for later in tool_msgs[k + 1:]:
                self.assertNotIn(later, json.dumps(obs))

    def test_oracle_sessions_all_pass(self):
        for placeholder in (False, True):
            for records, gold, _, _, session in self.batches:
                sess = copy.deepcopy(session)
                plans = {g["id"]: oracle_plan(g["episode"], placeholder) for g in gold["records"]}
                seal = run_session(gold, sess, plans, gold["batch"])
                res = astra_batch.replay(gold, sess, seal, "oracle-check")
                bad = [r for r in res["results"] if not r["keep"]]
                self.assertEqual(bad, [], f"placeholder={placeholder}")
                totals = sft.episode_weight_totals(res["rows"])
                self.assertTrue(all(abs(v - 1.0) < 1e-9 for v in totals.values()))
                fam = res["summary"]["by_family"]
                self.assertEqual(sum(v["accepted"] for v in fam.values()), len(gold["records"]))

    def test_corrupted_sessions_all_fail(self):
        counts = {}
        for records, gold, _, _, session in self.batches:
            for g in gold["records"]:
                for kind, calls, final in corrupted_plans(g["episode"]):
                    sess = {g["id"]: {"calls": [], "observations": [], "final": None, "rejected": None}}
                    one = {"batch": gold["batch"], "records": [g], "schema": gold["schema"]}
                    seal = run_session(one, sess, {g["id"]: (calls, final)}, gold["batch"])
                    r = astra_batch.replay(one, sess, seal, "corrupt")["results"][0]
                    self.assertFalse(r["keep"], f"{kind} kept on {g['episode']['id']}: {r}")
                    counts[kind] = counts.get(kind, 0) + 1
        self.assertTrue({"future_citation", "future_identifier", "status_swap", "forged_evidence",
                         "drop_required_calls", "unauthorized_proposal", "duplicate_call", "wrong_value",
                         "session_mismatch", "clarification", "disposition_mismatch"} <= set(counts))
        print("\ncorrupted sessions rejected:", json.dumps(counts, sort_keys=True), file=sys.stderr)

    def test_protocol_violations_close_the_session(self):
        records, gold, _, _, session = self.batches[0]
        sess = copy.deepcopy(session)
        ids = list(sess)
        bad = [{"schema": astra_batch.SCHEMA, "batch": gold["batch"], "id": ids[0], "round": 3, "action": "call",
                "call": {"name": "haven_device_state", "arguments": {"device_id": "x"}}},
               {"schema": astra_batch.SCHEMA, "batch": gold["batch"], "id": ids[1], "round": 0, "action": "call",
                "call": {"name": "rm_rf", "arguments": {}}},
               {"schema": "other", "batch": gold["batch"], "id": ids[2], "action": "final", "final": {}},
               {"schema": astra_batch.SCHEMA, "batch": gold["batch"], "id": ids[3], "action": "think"},
               {"schema": astra_batch.SCHEMA, "batch": gold["batch"], "id": "a-unknown", "action": "final", "final": {}}]
        obs, status = astra_batch.step(gold, sess, bad)
        self.assertEqual(obs, [])
        self.assertTrue(all(sess[i]["rejected"] for i in ids[:4]))
        seal = astra_batch.seal_record(gold, sess)
        res = astra_batch.replay(gold, sess, seal, "t")
        self.assertEqual(res["summary"]["accepted"], 0)
        self.assertEqual(res["summary"]["status"]["rejected_in_session"], 4)

    def test_replay_refuses_an_unsealed_or_altered_session(self):
        records, gold, _, _, session = self.batches[0]
        sess = copy.deepcopy(session)
        plans = {g["id"]: oracle_plan(g["episode"]) for g in gold["records"]}
        seal = run_session(gold, sess, plans, gold["batch"])
        with self.assertRaises(SystemExit):
            astra_batch.replay(gold, sess, None, "t")
        first = next(iter(sess))
        sess[first]["final"]["conclusion"] += " (edited)"
        with self.assertRaises(SystemExit):
            astra_batch.replay(gold, sess, seal, "t")

    def test_gold_commitment_is_framed_and_detects_tampering(self):
        records, gold, salt, digest, _ = self.batches[0]
        body = common.canonical(gold)
        manual = common.sha256_bytes(bytes.fromhex(salt) + len(body).to_bytes(8, "big") + body)
        self.assertEqual(manual, digest)
        tampered = copy.deepcopy(gold)
        tampered["records"][0]["episode"]["contract"]["expect_claims"][0]["status"] = "refused"
        self.assertFalse(common.check_commitment(salt, tampered, digest))

    def test_cli_round_trip_seal_before_reveal_and_audit_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            ep, priv = tmp / "eps.jsonl", tmp / "priv"
            common.write_jsonl(ep, EPISODES[:20])
            astra_batch.main(["export", "--episodes", str(ep), "--label", "rt", "--private-dir", str(priv),
                              "--out", str(tmp / "r0.jsonl"), "--n", "20"])
            gold = json.loads((priv / "rt.gold.json").read_text())
            plans = {g["id"]: oracle_plan(g["episode"], True) for g in gold["records"]}
            with self.assertRaises(SystemExit):
                astra_batch.main(["reveal", "--private-dir", str(priv), "--label", "rt", "--out", str(tmp / "g.json")])
            for rnd in range(astra_batch.MAX_CALLS + 2):
                session = json.loads((priv / "rt.session.json").read_text())
                replies = []
                for rid, s in session.items():
                    if s["final"] is None and not s["rejected"]:
                        calls, final = plans[rid]
                        replies.append({"schema": astra_batch.SCHEMA, "batch": "rt", "id": rid, "round": len(s["calls"]),
                                        "action": "call", "call": calls[len(s["calls"])]} if len(s["calls"]) < len(calls)
                                       else {"schema": astra_batch.SCHEMA, "batch": "rt", "id": rid, "action": "final",
                                             "final": final})
                if not replies:
                    break
                common.write_jsonl(tmp / f"reply{rnd}.jsonl", replies)
                astra_batch.main(["step", "--private-dir", str(priv), "--label", "rt", "--reply",
                                  str(tmp / f"reply{rnd}.jsonl"), "--out", str(tmp / f"obs{rnd}.jsonl")])
            astra_batch.main(["seal", "--private-dir", str(priv), "--label", "rt"])
            common.write_jsonl(tmp / "late.jsonl", [])
            with self.assertRaises(SystemExit):
                astra_batch.main(["step", "--private-dir", str(priv), "--label", "rt", "--reply", str(tmp / "late.jsonl"),
                                  "--out", str(tmp / "late-obs.jsonl")])
            astra_batch.main(["replay", "--private-dir", str(priv), "--label", "rt", "--out-dir", str(tmp / "r")])
            summary = json.loads((tmp / "r" / "rt.summary.json").read_text())
            self.assertEqual(summary["accepted"], 20)
            pub = json.loads((priv / "rt.public.json").read_text())
            astra_batch.main(["reveal", "--private-dir", str(priv), "--label", "rt", "--out", str(tmp / "g.json")])
            astra_batch.main(["verify", "--gold", str(tmp / "g.json"), "--commitment", pub["gold_commitment"]])
            a1 = astra_batch.audit_sample(tmp / "r" / "rt.kept-rows.jsonl", 50)
            a2 = astra_batch.audit_sample(tmp / "r" / "rt.kept-rows.jsonl", 50)
            self.assertEqual(a1, a2)
            self.assertEqual(a1["sampled"], 20)
            self.assertEqual(len({(x["episode"], x["teacher"]) for x in a1["sample"]}), 20)
            self.assertEqual(astra_batch.audit_sample(tmp / "r" / "rt.kept-rows.jsonl", 5)["sampled"], 5)
        with self.assertRaises(SystemExit):
            common.private_dir(HERE / "out" / "secrets")


# ------------------------------------------------------------------ Amendment 1: pools, structure, flips
import flip_pairs  # noqa: E402


class PoolsAndSplits(unittest.TestCase):
    def test_no_action_rate_is_frozen_from_public_dev_and_matched(self):
        r = pools.frozen_no_action_rate()
        self.assertEqual((r["n"], r["no_action_share"]), (538, 0.1673))
        eps, _, _ = gen_hare.make_episodes(SEED, 14, variants=2)
        kept = gen_hare.match_no_action_rate(eps, r["no_action_share"])
        self.assertLess(abs(pools.no_action_share(kept)["no_action_share"] - r["no_action_share"]), 1.0 / len(kept) * 3)

    def test_dispositions_by_family(self):
        d = collections.defaultdict(set)
        for e in EPISODES:
            d[e["family"]].add(pools.disposition(e))
        self.assertEqual(d["execute_refusal"], {"refusal"})
        self.assertEqual(d["household_denied"], {"insufficient_evidence"})
        self.assertEqual(d["chain3_conditional"], {"no_action_needed", "answer"})
        self.assertEqual(d["proposal_explicit"], {"answer"})

    def test_paired_variants_share_world_group_and_split(self):
        eps, _, _ = gen_hare.make_episodes(SEED, 4, variants=3)
        rows = gen_hare.training_manifest(eps, val_fraction=0.5)
        by = collections.defaultdict(list)
        for r in rows:
            by[r["scenario_group"]].append(r)
        self.assertTrue(any(len(v) > 1 for v in by.values()))
        for v in by.values():
            self.assertEqual(len({r["split"] for r in v}), 1)
            self.assertEqual({tuple(r["paired_variants"]) + (r["id"],) for r in v} and len(v), len(v))
        splits = collections.Counter(r["split"] for r in rows)
        self.assertEqual(set(splits), {"train", "train-val"})
        worlds = collections.defaultdict(set)
        for e in eps:
            worlds[e["lineage"]["scenario_group"]].add(json.dumps(e["world"], sort_keys=True))
        self.assertTrue(all(len(w) == 1 for w in worlds.values()))
        for r in rows:
            self.assertTrue(all(k in r for k in ("template_lineage", "structure", "entity_group", "disposition",
                                                 "sampling_weight", "template_ids")))

    def test_dev_manifest_covers_every_dev_pool_and_keeps_them_identifiable(self):
        rows = common.read_jsonl(HERE / "pools" / "dev_manifest.jsonl")
        self.assertEqual({r["pool"] for r in rows} >= {"hare-frozen-180", "hare-fresh-s0-179", "hare-untouched-179",
                                                        "querywriter-dev-84", "rule8-flip-pairs"}, True)
        self.assertEqual(sum(r["pool"] == "hare-frozen-180" for r in rows), 180)
        self.assertTrue(all(r["split"] == "dev" for r in rows))


class StructuralDedupe(unittest.TestCase):
    def test_renamed_copy_of_a_dev_episode_is_caught_by_structure(self):
        dev = next(e for e in common.bench.load_episodes() if e["family"] == "injection_output" and len(e["prompt"].split()) < 8)
        e = json.loads(json.dumps(dev))
        mapping = {s: f"zz{i}renamed" for i, (s, _) in enumerate(sorted(set(pools.entity_strings(dev)), key=lambda x: -len(x[0])))}
        blob = json.dumps(e)
        for old, new in mapping.items():
            blob = blob.replace(old, new)
        e = json.loads(blob)
        e["id"] = "train-renamed"
        rep = dedupe.check_items([dedupe.hare_item(e)], FP)
        self.assertEqual(len(rep["rejected"]), 1)
        self.assertTrue(rep["rejected"][0]["structure_hits"])

    def test_relabelled_dev_tenant_is_caught_by_the_graph_hash(self):
        T, qrun = common.load_querywriter()
        block = T.make_suite(qrun.SUITE_SEED, 12)[3]
        t = json.loads(json.dumps(block["tenant"]))
        names = {x: f"node{i}" for i, x in enumerate([u["id"] for u in t["users"]] + t["groups"] + t["sps"])}
        blob = json.dumps(t)
        for old in sorted(names, key=len, reverse=True):
            blob = blob.replace(f'"{old}"', f'"{names[old]}"')
        t2 = json.loads(blob)
        t2["users"] = list(reversed(t2["users"]))
        q = dict(block["questions"][0], id="train-q", question="A brand-new question wording about nothing in particular.")
        rep = dedupe.check_items([dedupe.query_item(q, t2)], FP)
        self.assertEqual(len(rep["rejected"]), 1)
        self.assertTrue(any(k.startswith("graph:") for k, _ in rep["rejected"][0]["structure_hits"]))

    def test_general_mix_is_checked_against_the_regression_set(self):
        try:
            reg = dedupe.regression_texts()
        except (FileNotFoundError, ImportError) as err:
            self.skipTest(f"regression files not fetched: {err}")
        texts = [t for e in EPISODES[:30] for t in dedupe.hare_item(e)["texts"]]
        rep = dedupe.check_general(texts + [reg["ifeval"][0], reg["mmlu_pro"][0], reg["bfcl"][0]])
        self.assertEqual([r["index"] for r in rep["rejected"]], [len(texts), len(texts) + 1, len(texts) + 2])

    def test_reserve_fingerprint_export_is_hashed(self):
        fp = dedupe.export_fingerprint([dedupe.hare_item(e) for e in EPISODES[:5]])
        blob = json.dumps(fp)
        self.assertNotIn(EPISODES[0]["prompt"][:30], blob)
        self.assertTrue(all(len(h) == 16 for h in fp["ngram_hashes"][:10]))


class EvidenceFlipPairs(unittest.TestCase):
    PAIRS = common.read_jsonl(HERE / "rule8" / "evidence_flip_pairs.jsonl")

    def test_committed_pairs_equal_a_fresh_build_and_validate(self):
        pairs, _ = flip_pairs.build_pairs()
        self.assertEqual(self.PAIRS, json.loads(json.dumps(pairs)))
        self.assertEqual(flip_pairs.validate(self.PAIRS), [])

    def test_balanced_flip_and_control_with_identical_requests_on_flips(self):
        kinds = collections.Counter(p["kind"] for p in self.PAIRS)
        self.assertEqual(kinds["flip"], kinds["control"])
        self.assertGreaterEqual(kinds["flip"], 60)
        self.assertTrue(all(p["request_identical"] for p in self.PAIRS if p["kind"] == "flip"))
        self.assertGreaterEqual(len({p["family"] for p in self.PAIRS}), 9)


if __name__ == "__main__":
    unittest.main()
