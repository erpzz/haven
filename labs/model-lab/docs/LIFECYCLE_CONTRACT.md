# Model lifecycle responses: contract (2026-10-27, merge/deploy owner)

Status: **decided; server side not yet implemented.** Codex implements it in one focused PR. Opus reviews,
integrates and deploys. The Mac client `ops/haven-core/slink-lab.py` already behaves this way on the client side,
and switches to the server's answers once they exist.

## What went wrong on 2026-10-27

The Lab's own records show the sequence:

1. `labctl load qwen36-35b-a3b --wait` started job `ba33d38b` at 20:17:51 UTC.
2. `labctl --wait` stops following after its default `--timeout 180`. It then printed `WAIT_TIMEOUT` and exited 2, but the server kept loading: its own deadline is `180 + size / 32 MiB/s`, about 830 s for the 22 GB file.
3. A second `load` reached `start_llama`. `engine.proc` was set by the load still in progress, so the Lab answered HTTP 400 *"Unload the current Lab-owned engine before selecting another compute lane."*
4. The engine became READY at 20:23:35. The load took 344 s and succeeded.

So it was **a client polling timeout, followed by a non-idempotent load, answered with a misleading error.** It was not a status race and not a failure. Two more cases are wrong in the same way:

- **Engine crashed:** after a `PROCESS_EXITED`, the same unload message appears.
- **A request is active:** "A request is active." does not say which model or what to do.

## Contract: `POST /api/engine/start {id, preset, overrides}`

The engine record gains `model_id`, `preset`, `profile` and `job_id` for the load that produced it, so a request can
be compared with what is already there. Every response has `outcome` and, if the caller must act, `action`.

| Current backend | Request | HTTP | `outcome` | Body adds | Starts a load? |
|---|---|---|---|---|---|
| none / STOPPED | any model | 202 | `STARTING` | `job_id`, `ready_deadline_s` | yes |
| Lab-owned, same model and profile, STARTING | same | 200 | `ALREADY_STARTING` | the existing `job_id`, `started_at`, `ready_deadline_s` | **no** |
| Lab-owned, same model and profile, READY | same | 200 | `ALREADY_READY` | `model_id`, `since` | **no** |
| Lab-owned, other model or profile, STARTING or READY | different | 409 | `CONFLICT_LAB_ENGINE` | `current{model_id, state, job_id}`, `action: "unload first (labctl unload)"` | no |
| Lab-owned, PROCESS_EXITED | any | 409 | `PREVIOUS_LOAD_FAILED` | `exit_code`, `log`, `action: "labctl unload to clear, then load"` | no |
| External backend connected (Strata) | any | 409 | `CONFLICT_EXTERNAL` | `current{kind, model}`, `action: "labctl disconnect (the service keeps running); stop haven-strata if the GPU is needed"` | no |
| Generation active | any | 409 | `BUSY_GENERATING` | `job_id` of the request | no |
| Validation (unknown model, fit, missing engine) | — | 400 | `REJECTED` | `error` (existing text) | no |

Rules:
- **An existing successful or in-progress load is never reported as an error.** HTTP 4xx is used only when the request cannot be satisfied as asked.
- A 409 changes nothing. Only an explicit `unload` or `disconnect` does.
- The `engine-start` job states stay `RUNNING`, `COMPLETED`, `FAILED` and `CANCELLED`. `COMPLETED` means READY; `FAILED` carries the existing error and the log path.

## Contract: `labctl load --wait`

- Following a load uses the server's `ready_deadline_s` plus 60 s, unless `--timeout` is given.
- `ALREADY_READY`: print it, exit 0.
- `ALREADY_STARTING`: follow the returned `job_id`, exactly as for a fresh load.
- Wait timeout: print `{"outcome": "STILL_STARTING", "job_id": …}` and exit **3** (not 2), with the note that the load continues and the same command re-attaches.
- Any 409: print the body and exit 4. Nothing was changed.
- `labctl job` accepts a unique id prefix.

## Tests Codex adds (labs/model-lab/tests)

1. A repeat start of the same model while STARTING gives `ALREADY_STARTING` with the same `job_id`. Only one process was launched, and `engine-key.txt` was not rewritten.
2. A repeat start while READY gives `ALREADY_READY`.
3. A different model while READY gives 409 `CONFLICT_LAB_ENGINE`, and the engine is untouched.
4. A start after `PROCESS_EXITED` gives 409 `PREVIOUS_LOAD_FAILED`.
5. A start with an external backend connected gives 409 `CONFLICT_EXTERNAL`.
6. `labctl --wait` past its timeout exits 3. Run again, it attaches to the same job.

## Out of scope

Automatic switching, retries, any change to Strata's unit, and new UI pages. The existing UI should show the same
`outcome` text instead of the old error.
