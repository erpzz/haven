# Opus — take the wheel on Haven

This is a prompt for the operator to send to Opus. Publication alone does not
start an agent or transfer credentials. Runtime checkpoint: 2026-10-26 UTC.

---

Opus, I want you to take full engineering and research steering of Haven. Explore
the project, understand the ambition, choose the highest-value next work, and
carry it through. You are an equal peer to Slinky, the Codex engineer who brought
up the Linux system. Challenge its recommendations when you have a better route.
You are not limited to finishing its task list.

This is also a friendly competition against GPT-6: who can make the most real
progress for Haven? Earn the result with working capabilities, useful discoveries
and reproducible evidence. Share useful work between peers. Commit counts,
benchmark gaming, excessive tests and unsupported breakthrough claims do not win.

## Mission and authority

Build Haven into a useful, privacy-first personal assistant and engineering
platform: reliable local intelligence, evidence-backed memory, dependable tool
use, learning from verified experience, and bounded autonomous work. Preserve
the wider multimodal, spatial, research, robotics and drone vision; today's text
runtime is a foundation, not the whole project. Read the relevant retained
requirements before changing a domain contract.

I authorize autonomous implementation, local runtime work, bounded experiments
and local training within this project. Choose priorities and technical direction,
make reversible decisions, and continue without repeatedly asking me for routine
approval. Historical research-only and phase-approval instructions describe their
original sessions; this direct assignment supplies the current scope. The limits
are no spending money or paid API calls and no wiping drives. Preserve Windows,
partitions, bootloader, existing work, ordinary sudo boundaries and recovery.
Keep inference private and Genesis stopped. Never ask me to paste credentials
into chat; use SSH/Keychain and interactive authentication.

Keep credentials, machine inventories, household/employer data, model weights,
adapters, runtime databases and raw model/agent transcripts out of GitHub. Use
owned branches and reviewable PRs; do not merge your own PR. Broad project
steering does not make unrelated data or physical systems available to operate.

## Start from the work that exists

Read root `AGENTS.md` and its short navigation/precedence files, then:

1. `ops/haven-core/CLAUDE_NEXT_SESSION.md` and `LINUX_MODEL_LAB.md` on PR #36.
2. `labs/intelligence-bakeoff/distillation/LINUX_PILOT.md` and its result JSON
   on the separate PR #37 checkout. Those paths are not on PR #36's ancestry.
3. `design/H02/R02/v1/INTEGRATION_SUMMARY.md` for intelligence, memory and
   authority intent; its dated recommendations are not current deployment facts.
4. Relevant HS-01 v2 sections in PR #34 when a topology decision requires them.

Explore more wherever it will change your decision. Do not ingest every archive
or repeat broad package/GPU/security audits. Some historical starter paths are
missing from this branch; report a relevant missing source rather than recreating
it or stalling the whole session. Use the current private access appendix on the
administration Mac for connection details and local receipts.

GitHub checkpoints:

- [PR #36](https://github.com/erpzz/haven/pull/36),
  `codex/slink-linux-model-lab-20261025`, stacked on bootstrap PR #35.
  Verified running code checkpoint: `23408d3487c1ae4c58cb489d64f5ba4aafd5e939`.
  Later handoff-only commits may follow it.
- [PR #37](https://github.com/erpzz/haven/pull/37),
  `codex/slink-distillation-pilot-20261025`, stacked on PR #29, which depends
  on bakeoff PR #28. Checkpoint: `42d682ebbf1eceddf4513bd7be21f3f03d947e17`.
- The Mac and server have separate runtime and distillation checkouts. Preserve
  those branches and their dependency history; do not casually merge them.

## What has actually happened

- `ssh haven` works with a dedicated encrypted key, strict host checking and
  password recovery preserved. I independently checked Slink's local public host
  fingerprint and confirmed it matches the Mac's pinned key. Authentication is
  not an outstanding task.
- Linux GPU support survived a real reboot with Secure Boot preserved. Package
  repair, maintenance, restricted ingress, persistent logs and private health
  checks are complete. Docker/NVIDIA support passed an ephemeral GPU visibility
  check; native inference and training exercised actual CUDA compute.
- The existing Python stdlib Model Lab runs as an ordinary user service on
  loopback 8877, reached through an owned SSH tunnel. Its launch URL is private.
  Qwen3.5-4B through pinned llama.cpp b11146 is loaded and ready. Real logs showed
  33/33 layers on CUDA. Short warm responses reported roughly 86–91 decode
  tokens/second and 0.17–0.18-second first output. A cold arithmetic answer was
  wrong. These observations establish operation, not broad model quality.
- Strata is already installed and prepared: official v0.2.6, Control 0.1.51,
  signed engine 0.1.50, both IQ2_XS shards verified, no need to download or hash
  them again. One authenticated response through the Lab completed: 27 tokens,
  0.834-second first output, 27.7 backend decode tokens/second. Unauthorized chat
  returned 401. The service was stopped cleanly and fast 4B restored.
- Strata's cold readiness took 868 seconds. The private appendix explains the
  measured storage bottleneck. Account for it; avoid repeated cold starts. Do
  not unplug the mounted root device or hide the problem with disk-flag edits.
- The separate Qwen3-0.6B LoRA pilot completed 40 steps in 18.016 seconds with
  2.63 GiB peak allocated CUDA memory. Three copying examples produced no fact
  or compositional-skill gain on 11 frozen probes. One retrieval probe changed;
  that is not generalized learning. No adapter was promoted.
- Real 4B tool-use results were 2/8 passes, then 3/8 after resource identifiers
  became discoverable and a whitespace-sensitive scorer was fixed. The second
  run selected the right tool on 7/8 tasks; all 8 transports completed. This was
  an interface/scorer change, not a training improvement. Only two verified
  training rows survived export. Failed targets remain unapproved.
- Tailscale client is installed but stopped pending intended-owner enrollment.
  LAN SSH works. Account ownership cannot be guessed from a handoff.

## Breakthroughs worth pursuing — you steer

My strongest candidate is a useful teacher-to-student learning loop: use the
prepared Strata model as a local teacher, validate its proposed tool trajectories
with deterministic code, build a diverse synthetic corpus, and see whether the
cached small student learns to handle genuinely unseen tasks. Generate teacher
data in one session, then release its GPU/RAM before training. Start with the
student that already fits. Text-output SFT is not token-logit GKD; do not override
memory gates or pretend the GGUF inference model is a trainable HF checkpoint.

Define success and freeze separate task families/templates before collecting
training examples. Compare the same baseline and adapter with identical settings.
Keep tool correctness, grounding, privacy/authority, unknown-fact behavior,
latency and memory visible. An independent held-out task should demonstrate
useful generalization, not memorized identifiers. A negative result with a clear
cause and a better next hypothesis is valuable. Do not keep tuning on the final
holdout or promote an adapter from a tiny synthetic score.

Other promising routes are reliable small-model tool contracts, retrieval and
evidence-backed memory with correction/deletion, or a thin durable coordinator
that completes a useful end-to-end task with cancellation and recovery. Inspect
the existing implementation before choosing; do not build a second framework.
Pick a different route if it has a stronger expected return and explain why.

Prepared 4B/Strata switching in the Lab is useful workflow work, not a required
first assignment. Currently the Linux button attaches an already-running Strata
service; it does not start or switch runtimes. Slinky inspected that gap but made
no implementation changes. If you implement it, reuse asynchronous jobs, visible
startup/cancellation and fixed service commands; keep keys server-side and stop
only the known Haven service. Preserve generic external-backend ownership.
Do not spend the whole session polishing this button if a capability experiment
would move Haven further.

## Working rhythm and finish

Use a short project tour to choose a concrete outcome, state your hypothesis and
start implementing. Keep one owner of the GPU at a time. Run focused checks for
what changed and one real end-to-end acceptance exercise. Broaden testing only
for an observed failure or material unresolved risk. Read saved receipts instead
of repeating successful installs, cold loads and training smoke tests.

Push useful checkpoints and concise sanitized results to GitHub as you go, so a
usage cutoff does not erase the handoff. Keep the private implementation log
current. If Slinky is working concurrently, coordinate through explicit branch
ownership and actual receipts; no automatic cross-chat memory is assumed.

Continue into the next useful slice when one finishes and resources remain.
Leave a usable runtime, stopped experimental services, exact commits/PRs, actual
results, limitations, rollback and the next best decision. Tell me what became
possible and what you learned. Take the wheel and make Haven meaningfully better.
