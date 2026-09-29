# Independent launcher attempt 1 — blocked on APP completion

Assignment 7; candidate read-only. At 2026-09-29T04:50:07Z the root launcher was invoked with evaluator-private runtime and fixed campaign deadline. It returned START_FAILED, child exit2. Actual app log: `Directory .../labs/ip01/haven/static does not exist`.

This is the developing APP's readiness failure, not a demonstrated launcher stop defect. Root/APP should complete their owned static/template assets, then QA can independently rerun start/status/duplicate-start/stop/restart/deadline. No directory or candidate file was created by QA to bypass it. Current launcher hash `5ee9fb5f92c9977be4754675ebe136bd13bf42758207a98abad907b065a9a656`; exact app/module hashes and failed command/log are retained in evaluator `lifecycle_obs/runs/launcher-20260929T045007.520408Z/`.

Evaluator issue also retained: the initial finding writer indexed a Windows-backslash path with a slash key and raised KeyError after retaining the launch failure. The evaluator was corrected to use `.as_posix()`; candidate source was unchanged. Independent control survived and was then stopped; no known workload residual remained. The failed launcher owner PID/birth will also be explicitly reconciled in the next bounded check.

Runtime's separate 11-case benign fault run passed its frozen candidate; see RUNTIME_OBSERVED.json. No model calls or final-suite starts.
