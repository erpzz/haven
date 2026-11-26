# Fixture provenance

These minimized JSON documents were assembled by hand from the pinned producers below. They contain invented assignments and test outcomes. Two identifiers and the namespace come from SpecterOps' public synthetic Entra sample so that a reviewer can reproduce an exact join.

| Input | How it was constructed |
| --- | --- |
| `entraops_eam.json` | One User with one eligible, tenant-root-scoped EntraID role assignment. Field names, principal classifications and nested RoleAssignments follow the per-system EAM documents read by the EntraOps exporter. |
| `entraops_opengraph.json` | Minimal graph with one AZUser, one tenant-qualified AZRole, one directed EO_EligibleForEntraRole, and ID selectors. Uses the node, relationship and property construction in the same exporter. |
| `maester_2x.json` | Minimized 2.3.0 Maester result with a serialized PowerShell version object, one synthetic failed test and one consolidated affected Group. The derived UniqueId and native Id are distinct. |
| `maester_3_preview.json` | Minimized rc83 report with schema 2.1, catalog version, tenant context, test applicability fields and a structured affected Group. The invented test deliberately repeats across reports. |
| `*.receipt.json` | Locally generated v1 sidecars with the exact file hash, assigned fixture run ID, origin, producer pin and synthetic coverage assertions. |
| `sample-path.json` | Replay of a local CE query against the official synthetic Entra archive. It retains the directed membership, sample object IDs, query, archive digest, collection receipt and observation time. Display labels on nodes were omitted. |

The exporters were inspected at these revisions:

- [EntraOps EAM reader and OpenGraph writer](https://github.com/Cloud-Architekt/EntraOps/blob/5bdaebd1f8c4d8a037025b312e9a05405649e378/EntraOps/Public/PrivilegedAccess/Export-EntraOpsPrivilegedEAMBloodHound.ps1)
- [Maester 2.3.0 result writer](https://github.com/maester365/maester/blob/7413c42d3fcc724dfea94d2726e690ddd364d914/powershell/internal/ConvertTo-MtMaesterResult.ps1) and [affected-object aggregation](https://github.com/maester365/maester/blob/7413c42d3fcc724dfea94d2726e690ddd364d914/powershell/internal/affectedobjects/Get-MtAffectedObject.ps1)
- [Maester rc83 result writer](https://github.com/maester365/maester/blob/2d659e85c1ae57162412c499283ae4b431392379/powershell/internal/report/ConvertTo-MtMaesterResult.ps1) and [preview schema](https://github.com/maester365/maester/blob/2d659e85c1ae57162412c499283ae4b431392379/website/docs/result-schema.md)

The tests construct malformed and contradictory variants in memory. None of the four export fixtures came from executing EntraOps or Maester.
