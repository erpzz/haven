# Visual system designs

All diagrams are proposed logical designs, not observed deployment topology. 'Forge' is a suggested local coding-worker label. The first version can occupy one existing computer; boundaries must be implemented, not assumed from boxes.

## 1. Three zones and the feedback boundary

```mermaid
flowchart TB
  U[Person A / Person B\nPhone or browser] --> H[Haven Core\nIntent, context, authority, job ledger]
  H -->|Bounded JobSpec| B[Forge Lab\nWritable source copy and coding agent]
  B --> T[Development tools\nShell, builds, tests, browser, debugger]
  B -->|Model request| M[Local model service\nOne request at a time initially]
  M -->|Proposed content / tool decision| B
  B -->|Diff and execution artifacts| Q[Independent QA\nSource, test and UI verification]
  Q --> R[Separate code / evidence reviewers]
  R -->|Disposition and verified evidence| H
  H -->|Approved release only| S[Staging / rollback controller]
  S -->|Observed outcome| H
  H --> K[Evidence and proposed skill memory\nVersioned, source-linked, privacy-scoped]
```

The inference service does not receive deployment credentials. The builder does not own production memory or its acceptance decision. Ordinary lab work is writable and executable.

## 2. What feeds back into Haven

```mermaid
flowchart LR
  A[Your requested improvement] --> B[Inspect pinned source]
  B --> C[Implement and test]
  C --> D[Independent check]
  D --> E[Reviewable change]
  E --> F[Approved staging]
  D -->|Failure evidence| C
  E --> G[Code artifact]
  E --> I[Test and resource evidence]
  E --> J[Proposed reusable lesson]
  G --> K[Haven records]
  I --> K
  J --> K
  K -->|Relevant verified context| B
```

This is code/evidence/skill feedback, not automatic model-weight training. A proposed lesson is not automatically a trusted rule.

## 3. Hardware placement, selected by bottleneck

```mermaid
flowchart TB
  A[Start: existing desktop\n64 GB RAM + 8 GB GPU\nCore, lab and small local model]
  A -->|Need isolation / availability| B[Dedicated small x86 host\n32 GB RAM + 1 TB SSD\nCore or coding tools]
  A -->|Need stronger model fit| C[24 GB GPU workstation\n64 GB RAM + 1–2 TB SSD]
  A -->|Need sensor-side compute| D[Later edge node\nMicrocontroller / Jetson / Pi accelerator]
  B -->|Private authenticated inference requests| C
  D -->|Selected evidence, not authority| B
  E[Phone / existing screen\nOptional fixed USB camera] --> B
```

These branches are alternatives driven by measured needs, not a required shopping sequence. Edge TOPS and core language-model capacity are different. No robot or flight controller is connected by this diagram.
