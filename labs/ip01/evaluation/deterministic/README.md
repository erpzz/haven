# Independent deterministic development harness

Copy this complete directory to a reviewed evaluator directory **outside the candidate source tree** before running. Use the candidate's provisioned Python environment. All snapshots, private stores, caches and reports are written below the copied harness. Source remains read-only. Never run against a real account, existing app database or model gate.

`python -B prepare.py --candidate <candidate> --smoke`

Omit `--smoke` to execute the 150-case deterministic development portion. This command does not authorize a final deterministic suite. Model lifecycle, browser and protected-pilot assets are intentionally absent. The smoke executes two actual private A/B and finite-grant workflows; it is not the full validation denominator.

Synthetic grant expiry is computed from execution-time UTC plus one hour. This does not extend any campaign or model-gate expiry. Every run snapshots/hashes candidate imports before execution and checks source identity afterward; failed outputs are retained in timestamped private runs.

The 104 vector cases retain 26 components times four phases. Seventy-six perturb private backing dependencies or process configuration; 28 perturb seven actual constants in evaluator memory. These directly call the actual authority checker on an unchanged sealed vector. They do not claim 104 HTTP live reconfiguration flows. Some identity/availability domains are coupled. Exact 8 MiB derivative boundary is a serializer fault adapter after real decode; separate real JPEG inputs test natural below/above derivative size. See executable scenarios for limits.

No DBs, browser profiles, raw logs, model artifacts, pilot families or protected expected answers are included. Reusing the harness does not establish protected filesystem enforcement or final campaign qualification.
