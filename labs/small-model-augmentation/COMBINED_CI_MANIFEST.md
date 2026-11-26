# Combined CI composition — DO NOT MERGE

This branch exists only to test the exact current-head additive files from the small-model augmentation workstream together on a clean GitHub runner.

Source heads:
- #127: `1c64db3611018931d8b724bd06e7ed1e77f76bef`
- #128: `48ed796b0b7a4a552b99a77826fc5e55f77a26ad`
- #129: `0978056643949128f6fc829ce5257694669d8bde`
- #130: `becd24f7c9ff34cb4b210b52ea51fe9c583c96d8`
- #131: `eecc8172d0a7b8d92c54938996e0e6eefd604b00`
- #132: `65889b423fd7d907fe66253f3b278c4bb06026e6`
- #133: `73017e344ae849e49eb820682bcec446936465b1`

Base main: `53387e74a0ad90786ac3ea16753c8ad99142e9df`.

The files are copied from those exact refs without integrating them into product/runtime paths. Passing this CI proves only clean Linux/Python regression and cross-package coexistence. It does **not** satisfy Mac/Hermes/llama.cpp/APFS/MCP/live integration or independent-review requirements.
