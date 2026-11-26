---
id: windows-ad.kerberos-detection
title: Kerberos, NTLM and replication abuse: detection with Windows security events
domain: windows-ad
topic: detection
source_url: https://learn.microsoft.com/windows/security/threat-protection/auditing/event-4769
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Windows Server security auditing (event IDs stable across 2012 R2–2025)
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [active-directory, windows-event-log, kerberos]
prerequisites: []
see_also: [https://learn.microsoft.com/windows/security/threat-protection/auditing/event-4768, https://learn.microsoft.com/windows/security/threat-protection/auditing/event-4662]
---

# Kerberos, NTLM and replication abuse: detection

Defensive reference: what each technique looks like in Windows security logs on domain controllers, and which control removes it. Event IDs require the matching "Advanced Audit Policy" subcategories to be enabled on DCs.

## Kerberoasting (ATT&CK T1558.003)

Any domain user can request a service ticket (TGS) for an account with a `servicePrincipalName` and crack it offline if that account's password is weak.
- **Telemetry:** event **4769** (service ticket requested). Watch **Ticket Encryption Type 0x17 (RC4-HMAC)** where AES is normal, and one account requesting many different SPNs in a short time.
- **Control:** gMSAs or 25+ character random passwords for service accounts; AES-only (`msDS-SupportedEncryptionTypes`); remove unneeded SPNs; keep SPN accounts out of privileged groups.

## AS-REP roasting (T1558.004)

Accounts with "Do not require Kerberos preauthentication" (`DONT_REQ_PREAUTH`) return crackable material without a password.
- **Telemetry:** event **4768** with **Pre-Authentication Type 0**.
- **Control:** clear the flag; audit for it periodically.

## DCSync (T1003.006)

An account with directory replication rights asks a DC for password hashes, including krbtgt's.
- **Telemetry:** event **4662** on a DC from a non-DC account, with properties `1131f6aa-9c07-11d1-f79f-00c04fc2dcd2` (DS-Replication-Get-Changes) and `1131f6ad-9c07-11d1-f79f-00c04fc2dcd2` (DS-Replication-Get-Changes-All). Also replication traffic from a non-DC IP.
- **Control:** only DCs (and an Entra Connect account using password hash sync) hold these rights; review the domain root ACL.

## Golden / silver tickets (T1558.001 / T1558.002)

Forged tickets signed with the krbtgt key (golden) or a service key (silver). Indicators include:
- ticket lifetimes or encryption types that do not match domain policy;
- 4769 events without a preceding 4768 for the account;
- logons by accounts that do not exist or are disabled.
Remediation: rotate krbtgt twice; investigate how the key was obtained (DCSync, DC backup, NTDS.dit).

## Delegation

- **Unconstrained delegation** on a non-DC computer lets that computer impersonate any user who authenticates to it, including DCs coerced to authenticate.
- **Constrained delegation** with protocol transition, and **resource-based constrained delegation** (`msDS-AllowedToActOnBehalfOfOtherIdentity`, writable by anyone with write on the computer object), are common escalation paths.
- Inventory all three; admin accounts belong in Protected Users and are marked sensitive.

## Account and group changes

| Event | Meaning |
|---|---|
| 4720 | user account created |
| 4728 / 4732 / 4756 | member added to a security-enabled global / local / universal group |
| 4672 | special privileges assigned to a new logon (admin-equivalent logon) |
| 4624 | successful logon; type 3 network, 10 RemoteInteractive (RDP) |
| 4625 | failed logon; status 0xC000006A bad password, 0xC0000064 unknown user |
| 4740 | account locked out |

## NTLM

NTLM relay and pass-the-hash (T1550.002) depend on NTLM being accepted. Defences:
- SMB signing required;
- LDAP signing and channel binding on DCs;
- Extended Protection for Authentication on AD CS web enrolment and Exchange;
- NTLM auditing, then restriction.

## Common false positives

RC4 tickets from legacy systems that really need RC4 (document them), vulnerability scanners requesting many SPNs, and Entra Connect's legitimate replication rights.
