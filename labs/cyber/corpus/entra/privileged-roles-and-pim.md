---
id: entra.roles.pim
title: Directory roles, role assignments and Privileged Identity Management
domain: entra
topic: privileged-access
source_url: https://learn.microsoft.com/entra/id-governance/privileged-identity-management/pim-configure
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Microsoft Graph v1.0 unifiedRoleAssignment / unifiedRoleEligibilitySchedule
license: original-summary (Haven authored; Microsoft Learn linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [entra-id, pim, microsoft-graph]
prerequisites: [Entra ID P2 or Entra ID Governance for PIM]
see_also: [https://learn.microsoft.com/entra/identity/role-based-access-control/best-practices, https://learn.microsoft.com/graph/api/resources/rolemanagement]
---

# Directory roles, role assignments and PIM

## Concepts

- **Role definition**: a set of permissions. Built-in roles have fixed template ids (Global Administrator is `62e90394-69f5-4237-9190-012177145e10`; Privileged Role Administrator `e8611ab8-c189-46e8-94e1-60213ab1f814`; Privileged Authentication Administrator `7be44c8a-adaf-4e2a-84d6-ab2649e08a13`).
- **Active assignment** (`/roleManagement/directory/roleAssignments`): the principal holds the role now. With PIM, active assignments can be permanent or time-bound.
- **Eligible assignment** (`/roleManagement/directory/roleEligibilitySchedules`): the principal must *activate* (with MFA, justification, optional approval) before holding the role, for a limited duration.
- **Scope**: `directoryScopeId` of `/` is tenant-wide; an administrative unit scope (`/administrativeUnits/<id>`) limits the role to members of that unit.

## What good looks like

- Fewer than five permanent Global Administrators. Microsoft recommends keeping Global Administrator to a small number, and at least two for resilience. The emergency-access accounts are typically permanent Global Administrators and are the exception to "everything eligible".
- Privileged roles are eligible, not permanently active, for human admins; activation requires MFA (ideally phishing-resistant) and, for the highest roles, approval.
- Admin accounts are cloud-only (not synchronised from on-premises AD), so an on-premises compromise does not extend to the cloud tenant.
- Role-assignable groups (`isAssignableToRole: true`) are used for group-based assignment, because only privileged roles can manage their membership.

## Privilege-escalation paths to check

- Principals holding **Privileged Role Administrator** can assign any role, including Global Administrator.
- **Application Administrator / Cloud Application Administrator** can add credentials to service principals; if a service principal holds a privileged role or a high application permission, this is an escalation path.
- Service principals with the Graph application permission `RoleManagement.ReadWrite.Directory` can grant themselves any role. `AppRoleAssignment.ReadWrite.All` can grant any application permission, including that one.
- Owners of a group that is assigned a role (if not role-assignable) can add themselves.

## Assessment procedure

1. Collect active and eligible assignments with principal type (user, group, service principal).
2. Count permanent active assignments to privileged roles; separate emergency accounts.
3. Expand group-based assignments to members.
4. Flag guests and synchronised accounts holding privileged roles.
5. Flag service principals holding directory roles or privileged Graph application permissions.

## Common false positives

- Counting eligible assignments as standing privilege.
- Treating emergency-access Global Administrators as excess.
