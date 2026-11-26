# Combined CI composition — DO NOT MERGE

Synthetic validation branch based on #115 head `7f5af0d549fe89056181942b268b01573cf86ce5`.

Exact augmentation source heads:
- #127 `1c64db3611018931d8b724bd06e7ed1e77f76bef`
- #128 `48ed796b0b7a4a552b99a77826fc5e55f77a26ad`
- #129 `0978056643949128f6fc829ce5257694669d8bde`
- #130 `becd24f7c9ff34cb4b210b52ea51fe9c583c96d8`
- #131 `eecc8172d0a7b8d92c54938996e0e6eefd604b00`
- #132 `65889b423fd7d907fe66253f3b278c4bb06026e6`
- #133 `73017e344ae849e49eb820682bcec446936465b1`

A bridge test under #115's existing watched test path launches the combined augmentation suite in the same clean GitHub Actions checkout. This proves Linux/Python-3.11 regression/coexistence only; it is not a Mac/Hermes/llama.cpp/APFS/MCP or independent-review receipt.
