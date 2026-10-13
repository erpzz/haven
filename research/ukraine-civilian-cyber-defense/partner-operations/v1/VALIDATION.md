# dComms contribution validation

Patch base: a9380cae07cf11e0343c2a719689937fd1ae80a9
Patch file: dcomms-synapse-admin-registration.patch
Target path: docs/synapse.md
SHA-256: 89cbc1fba03e6353fda7c0b7e3a2b3ac3dbaea5fe6c080a7271dcb614ec5dc2d

Executed locally:
- Both extracted Bash blocks: bash -n, success.
- git apply --check: success.
- git apply followed by exact byte comparison: success.
- Curl replaced with a local recorder; synthetic token was present only in stdin,
  absent from argv/stdout/stderr.
- JSON uses_allowed=1 and expiry_time approximately 24h ahead in milliseconds.
- Target fixed to loopback; -q first; no redirect-following option.
- Empty, quote, backslash, space token inputs: no curl call.
- Curl stub exit 22: propagated to snippet caller.

NOT executed:
- No Docker daemon available.
- No real Synapse, admin account, registration API, invitation or user created.
- No organization's systems, private data or credentials accessed.

A maintainer should apply the patch with git apply --check, then git apply, and
verify both snippets on an expressly authorized disposable Synapse deployment.
Do not treat mocked validation as deployment acceptance.
