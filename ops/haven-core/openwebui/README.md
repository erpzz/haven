# Haven chat (Open WebUI) on Slink

Open WebUI is Haven's everyday chat. Haven Model Lab stays the operator console for
loading models, GPU/RAM, diagnostics and workers.

```
browser ──ssh tunnel──▶ Open WebUI 127.0.0.1:8878 ──gateway key + signed user JWT──▶
  Model Lab /v1 (127.0.0.1:8877) ──Lab.generate: routing, consent, limits, receipts──▶ runtime / workers
```

Open WebUI never talks to llama.cpp, Strata or a worker directly. The Lab's `/v1`
gateway (`labs/model-lab/gateway.py`) only accepts loopback clients holding a gateway key,
and verifies each user's identity from Open WebUI's HS256-signed `X-OpenWebUI-User-Jwt`.
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
  route, model, metrics and tool names. Prompts and replies are not recorded.
- **Files** go to the model as full text, because no embedding model is downloaded.
  Images are refused by text models.
- **Settings are code.** `ENABLE_PERSISTENT_CONFIG=false`, so `install.sh` decides
  connections, signup role and tasks on every start. Admin-UI changes to those revert at restart.

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
