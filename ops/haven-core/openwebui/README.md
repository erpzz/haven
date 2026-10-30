# Haven chat (Open WebUI) on Slink

Open WebUI is an **interim, optional chat frontend**, not Haven's product UI.
Haven Model Lab remains the operator console for model loading, GPU/RAM,
diagnostics, workers and experiment capabilities. The first-party Haven UI must
own model selection, orchestration and transparent routing.

```
browser ──ssh tunnel──▶ Open WebUI 127.0.0.1:8878 ──gateway key + signed user JWT──▶
  Model Lab /v1 (127.0.0.1:8877) ──Lab.generate: routing, consent, limits, receipts──▶ runtime / workers
```

Open WebUI never talks to llama.cpp, Strata or a worker directly. The Lab's `/v1`
gateway (`labs/model-lab/gateway.py`) only accepts loopback clients holding a gateway key,
and verifies each user's identity from Open WebUI's HS256-signed `X-OpenWebUI-User-Jwt`.
Missing or invalid shared JWT-secret configuration refuses all frontend requests
(HTTP 503); direct owner CLI keys remain independent.
Open WebUI `admin` users become Haven owners and `user` accounts become members. Pending
accounts can't chat.

| What | Owner | Member |
|---|---|---|
| Slink runtime (`haven-slink`) | yes | yes, once shared (see below) |
| Automatic, enrolled workers, Mac | yes | refused by Haven |
| Hosted Claude Code / Codex lanes | yes, after `/haven consent` in that chat | refused by Haven |
| Other users' chats | no (`ENABLE_ADMIN_CHAT_ACCESS=false`) | no |
| Load or unload models, diagnostics | Model Lab only | no |

## Use it from the Mac

```bash
ssh -N -L 8878:127.0.0.1:8878 haven
```

Then open <http://127.0.0.1:8878>. The first account created becomes the admin, so create
yours first. Household members sign up and wait as *pending* until you approve them under
Admin → Users.

To let members use the Slink model: Admin → Models → **Slink** → Access → Public (read).
Haven still checks every request, so sharing other entries grants nothing.

In any chat:
- `/haven status` shows the loaded model, its context, GPU/RAM, who holds the GPU and (owner only) the workers. Nothing is sent to a model.
- `/haven consent` lets this one chat use the selected hosted lane. Without it, nothing leaves the house.

## Behaviour worth knowing

- **One GPU slot.** Requests queue for up to 180 s, then report busy. Title, tag,
  follow-up and query generation are off so they don't take the slot from your reply.
- **Output length** follows the loaded context. With no `max_tokens`, a reply may use what
  the conversation leaves free, up to 16,384 tokens. Requests that wouldn't fit are refused
  rather than truncated.
- **Stop** closes the stream, and the Lab job is cancelled.
- **Tools.** Open WebUI's built-in tools (time, memory, chat search, knowledge, notes)
  run inside Open WebUI under the user's own permissions. Haven passes the tool calls and
  results through on the Lab-managed llama.cpp runtime. Other lanes answer in text, and
  the receipt records `tools_dropped`.
- **Receipts.** Each request appends to `~/.local/share/haven-model-lab/gateway-receipts.jsonl`:
  requested selector, resolved Lab provider, reported model, metrics and tool names.
  Prompts and replies are not recorded. Non-stream replies include `haven.routing`;
  streaming replies include the same object in the final SSE chunk. This metadata
  is for Haven-native clients; Open WebUI may not render vendor extension fields.
  Route aliases (`haven-slink` / `haven-auto`) are **not installed model IDs**.
  Fallback is marked `UNDETERMINED` until the Lab records actual fallback events;
  digest provenance is declared evidence, not independent weight attestation.
- **Files** go to the model as full text, because no embedding model is downloaded.
  Images are refused by text models.
- **Settings are code.** `ENABLE_PERSISTENT_CONFIG=false`, so `install.sh` decides
  connections, signup role and tasks on every start. Admin-UI changes to those revert at restart.

## Tool schemas and the prompt cache

Open WebUI attaches its built-in tool schemas to every request. With all 30 of them, the
first request after a model load measured **116.9 s** to first token on the 35B
(5,437 prompt tokens, CPU-bound prefill while other CPU jobs ran). Every later request,
**including a brand-new chat**, reuses that prefix from llama.cpp's prompt cache
(0.74 s to first token). So the cost is per model load, not per chat.

**Don't vary tools per message.** It would change the tool block at the start of the prompt
and invalidate the shared cache on every turn. Instead, the gateway applies a
**deterministic per-frontend withhold list**: `~/.local/share/haven-model-lab/gateway-tools.json`
(mode 0600). Edits take effect on the next request.

```json
{"open-webui": {"withhold": ["list_knowledge_bases", "search_knowledge_bases", "query_knowledge_bases",
  "grep_knowledge_files", "search_knowledge_files", "query_knowledge_files", "view_knowledge_file",
  "create_calendar_event", "update_calendar_event", "delete_calendar_event", "search_calendar_events",
  "search_notes", "view_note", "write_note", "replace_note_content", "create_tasks", "update_task"]}}
```

Measured on the test frontend with this list (knowledge, calendar, notes and tasks
withheld; time, memory, chat search and ask-user kept):

| | Prompt tokens | Cached | First token |
|---|---|---|---|
| Cold, all 30 tools | 5,437 | 0 | 116.9 s |
| Cold, 13 tools | 2,242 | 0 | 46.7 s |
| New chat after that | 2,246 | 2,222 | 1.29 s |

**Withheld isn't removed.** The tools stay installed and enabled in Open WebUI. To bring them back:
- in one chat: `/haven tools all`, or `/haven tools default` to undo. This is per user and per chat, held in Lab memory, and cleared by a Lab restart.
- for one model: add `"models": {"<model id>": {"withhold": []}}` under the frontend entry.
- everywhere: remove the frontend's entry, or delete the file. This takes effect on the next request.

The production frontend (`open-webui`) has used this list since 2026-10-28 03:13 UTC.
The previous file is kept as `gateway-tools.json.bak-20261028T031333Z`. To roll back, restore
that copy, or delete the `open-webui` entry.

`/haven tools` lists what was supplied and withheld and each schema's estimated cost.
Receipts and the routing trace record the supplied and withheld names, and llama.cpp's
`prompt_cached_tokens` / `prompt_processed_tokens` for every request.

## Install, update, roll back (on Slink)

```bash
sh ops/haven-core/openwebui/install.sh                                   # prod, :8878
HAVEN_OWUI_INSTANCE=test HAVEN_OWUI_PORT=8879 sh ops/haven-core/openwebui/install.sh
sh ops/haven-core/openwebui/rollback.sh                                  # stop + revoke key
```

`install.sh` is idempotent. It pins Open WebUI 0.11.4 with CPU-only torch and reuses a
registered gateway key (`HAVEN_OWUI_ROTATE=1` issues a new one). Secrets live only in
`~/.config/haven-openwebui*/env` and the Lab data dir, all mode 0600.

`rollback.sh` stops the unit and revokes its key. Chats and accounts stay in
`~/.local/share/haven-openwebui/data*`. To roll back the Lab gateway itself, check out the
previous Lab revision in `~/projects/haven` and restart `haven-model-lab.service` while no
engine is loaded.
