# Threat hunting pack: CERT-UA UAC-0277 / ClickFix (September–October 2026)

**Primary source:** [CERT-UA, UAC-0277, published September 30, 2026](https://cert.gov.ua/article/6319983). The Ukrainian government's [October 6 public advisory](https://www.kmu.gov.ua/news/ia-ne-robot-cert-ua-fiksuie-masove-poshyrennia-shkidlyvoho-prohramnoho-zabezpechennia) corroborates the public warning.

## What this contributes

Four **read-only Microsoft Defender for Endpoint Advanced Hunting KQL** searches for authorized defenders:

1. `UAC0277_remote_msi_execution.kql` — find `msiexec.exe` processes whose command lines reference a network URL (explicit CERT-UA recommendation).
2. `UAC0277_clickfix_script_launch.kql` — potential browser/Explorer initiated shell or script execution with network payload clues (broad hypothesis only).
3. `UAC0277_driver_dll_artifacts.kql` — locate published vulnerable driver/DLL filenames (`PDFWKRNL.sys`, `spkvol.dll`); filename-only matches need independent validation.
4. `UAC0277_task_persistence.kql` — search process command lines for the published optional `psychedelicloveUtils` scheduled-task name; misses direct Windows API or other methods.

**Attribution:** these searches are grounded in a publicly reported campaign identifier, not an assertion about the geographic location, nationality, or ownership of any detected infrastructure. No offensive use or targets are supplied.

## Operational steps

1. Run only within a tenant you administer or have explicit authorization to investigate; open Defender XDR > Hunting > Advanced hunting, paste **one** `.kql` file, and review results.
2. Check prevalence, device/user context, executable signature/hash, parent-child process relationships, timestamps, and any related security incidents.
3. Escalate confirmed suspicious activity through the organization's incident-response procedures; preserve evidence first.
4. Review Microsoft Vulnerable Driver Blocklist, constrained software installation, and browser extension policies with the environment's owners. Do **not** automatically lock down all endpoints based on these queries.

## Validation status

- This is a **draft hunting pack**, not an automated blocking rule or production-certified analytics rule.
- Queries were reviewed for common MDE Advanced Hunting schema fields, but **have not been executed inside an MDE tenant**. They can return false positives or miss activity depending on telemetry retention and collection coverage.
- Findings may include personally identifiable information. Export and share only with appropriate permissions and minimization.
- If detection content is translated, coordinate review with a Ukrainian-speaking analyst before operational use.

This work is not affiliated with or endorsed by CERT-UA, DSLU, Microsoft, or any Ukrainian organization.
