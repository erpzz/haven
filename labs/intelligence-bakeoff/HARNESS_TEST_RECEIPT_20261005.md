# Harness validation receipt — 2026-10-05

Scope: deterministic synthetic-tool/scorer logic only. **Not** a model, Hermes, GPU, subscription, or Windows qualification.

A local isolated Python 3 environment recreated the current synthetic-tool, scorer, Hermes identity-binding handler and unit-test bytes from this branch and ran:

```
python -m unittest discover -s tests -v
```

Result: **6 tests passed / 0 failed**.

The suite was rerun after moving the Hermes plugin into the actual project-discovery path `.hermes/plugins/haven-bakeoff/` and updating its documented keyword-only post-tool hook handling.

Covered:
- cross-user private note is not disclosed;
- current revision selection;
- proposal remains inert (`executed:false`);
- scorer rejects a forbidden tool;
- Hermes-side handler overwrites model-supplied principal with the authenticated principal supplied out-of-band;
- proposal IDs are deterministic.

The environment could not reach GitHub over the container network, so this was not a fresh branch checkout. It was a local execution of the exact relevant source text fetched through the connected GitHub tool. The real Windows host must rerun `python -m unittest discover -s tests -v` after checkout.

No external model call, account login, model download, paid API, or physical/device operation was performed.
