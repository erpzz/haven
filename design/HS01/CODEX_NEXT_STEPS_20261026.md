# Codex: HS01 next steps from the architecture thesis (2026-10-26)

Source: [ARCHITECTURE_BREAKTHROUGH_THESIS_20261026.md](ARCHITECTURE_BREAKTHROUGH_THESIS_20261026.md). These are suggestions for Codex to take on, not commitments.

**Ground rules.**
- No GPU use and no heavy disk reads on Slink until the paradigm-bakeoff session releases the host.
- Work on your own branches. Do not edit the frozen `tool_sft` benchmark or verifier (PR #45). Do not merge your own PRs.
- Anything that changes the host or downloads weights needs the owner's yes first.

1. **Finish the cold-start diagnosis** (EXP-01; your [OVERNIGHT checkpoint](https://github.com/erpzz/haven/blob/codex/hs01-real-diagnostics-20261026/ops/haven-core/OVERNIGHT_20261026.md) already found a 480 Mbit/s link).
   - After the release, run `probe-strata-storage.py` once. Expected: 35–45 MiB/s.
   - Then give the owner a one-page decision:
     - (a) Move the X9 to a USB 3 port or cable. Expected: at least 300 MiB/s and ready in 150 s or less.
     - (b) Use an internal SSD. These are currently unmounted NTFS; reformatting is the owner's decision, so do not touch them.
   - After the owner's change, run exactly one cold start with the same config as before. **Kill:** if it is less than 2× faster, the link is not the dominant cause.
2. **Add a newer llama.cpp engine beside the current one.**
   - The pinned b11146 (2026-09-23) predates `--moe-cache-mib` ([PR #29887](https://github.com/ggml-org/llama.cpp/pull/29887), merged 2026-10-07).
   - Add a checksummed b11889+ build as a second Lab engine. Keep the current default, record the engine for every result, and add unit tests now.
3. **Prepare the weights-approval packet for M1/Q1.** Do not download anything yet.
   - List Qwen3.6-35B-A3B with its exact HF revision, a Q4-class GGUF and an IQ2_XS GGUF, sizes, sha256 and license.
   - M1 compares llama.cpp `--cpu-moe --moe-cache-mib ~5000` with Strata IQ2_XS on the 110 held-out episodes.
   - Expected: 18–30 tok/s and at least 76/110. **Kill:** below 12 tok/s or below 70/110.
   - Load it only after step 1. At 40 MiB/s, loading 21 GB takes about 8 minutes.
4. **Fix the execution-request contract.** This is the cheapest lever on the tool score.
   - Both the 4B (6 cases) and Strata (0/40) substitute a proposal when asked to execute.
   - Check whether the runtime contract and tool schema make the correct response reachable.
   - Preregister one prompt/schema variant for the 4B, with verifier v3 unchanged.
   - Expected: +4 to +6 episodes. **Kill:** below +2, or any new authority or leak flag.
   - The GPU run happens only after the release, coordinated with the PR #45 owner.
5. **Add an opt-in MTP setting to the Lab** (S1).
   - Add a `draft-mtp` profile field ([PR #22673](https://github.com/ggml-org/llama.cpp/pull/22673)) and a greedy-equality check.
   - First read the GGUF metadata (no GPU needed) to see whether the pinned Qwen3.5-4B Q4_K_M still has its MTP tensors. If it does not, a new GGUF needs approval.
   - Expected: 1.25–1.5× decode with byte-identical output. **Kill:** below 1.15×, or any divergence.
6. **Try to falsify the thesis.**
   - Check its [S]/[I] claims, especially that Qwen3.8-Flash-Next is ~125B with 6B active and a 51.2B Engram table, and the RAM-bandwidth ceiling math.
   - Post corrections on issue #40.

**Not for Codex:**
- C1, the oracle-union analysis, needs Claude's private per-episode results (PR #45 owner).
- The paradigm bake-off belongs to its own session.
