---
id: windows-ad.tiering
title: Active Directory privileged groups, tier 0 and AdminSDHolder
domain: windows-ad
topic: privileged-access
source_url: https://learn.microsoft.com/windows-server/identity/ad-ds/plan/security-best-practices/appendix-b--privileged-accounts-and-groups-in-active-directory
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Windows Server AD DS 2016–2025 functional levels
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [active-directory, windows-server]
prerequisites: []
see_also: [https://learn.microsoft.com/security/privileged-access-workstations/privileged-access-access-model, https://learn.microsoft.com/windows-server/identity/laps/laps-overview]
---

# Active Directory privileged groups, tier 0 and AdminSDHolder

## Tier 0: what controls the domain

Anything that can control a domain controller or the identities on it is tier 0:
- domain controllers;
- the AD CS certificate authorities;
- the Entra Connect (sync) server and AD FS servers;
- backup systems holding DC images;
- virtualization hosts running DCs;
- any account or group with rights over these.

Compromise of any tier 0 asset equals compromise of the domain. Hybrid tenants extend that to the cloud through synchronisation.

## Groups that are effectively domain control

Enterprise Admins, Domain Admins, Schema Admins and Administrators (built-in), plus the "operator" groups that can reach DCs or their data:
- Account Operators: can modify most non-protected accounts and groups.
- Backup Operators: can back up DC files, including NTDS.dit, and log on to DCs.
- Server Operators: can manage DC services.
- Print Operators: can load drivers on DCs.
- DnsAdmins: historically able to load a DLL into the DNS service on DCs.

Members should be few, named, and use dedicated admin accounts from privileged access workstations.

## AdminSDHolder and SDProp

Accounts that are (or were) members of protected groups get `adminCount=1`. Every 60 minutes by default, the SDProp process overwrites their ACLs with the ACL on `CN=AdminSDHolder,CN=System,<domain>`. Two assessment consequences:
1. An ACE added to AdminSDHolder propagates to every protected account. It is a persistence technique, so AdminSDHolder's ACL must be reviewed.
2. `adminCount=1` on an account no longer in a protected group shows past privilege, and the account keeps the hardened ACL until it is cleaned up.

## Controls to verify

- Protected Users group for admin accounts: no NTLM, no DES/RC4 Kerberos, no delegation, short TGT lifetime.
- "Account is sensitive and cannot be delegated" on admin accounts.
- Windows LAPS (built into supported Windows since the April 2023 updates) for unique local administrator passwords, with password backup to AD or Entra ID and restricted read access.
- No standing tier 0 membership for service accounts; gMSAs for services.
- krbtgt password rotated periodically, **twice** in a row (with replication between) after a suspected compromise.

## Assessment procedure

1. Enumerate the members, recursively, of every group listed above.
2. List objects with rights over tier 0 objects, especially non-default ACEs on the domain root, AdminSDHolder, DCs' computer objects and GPOs linked to the Domain Controllers OU.
3. Flag stale `adminCount=1` accounts, admins outside Protected Users, and service accounts with SPNs in privileged groups.

## Common false positives

Built-in default members (e.g. Administrators containing Domain Admins and Enterprise Admins) are expected. Report non-default members only.
