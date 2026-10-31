---
id: m365.exchange
title: Exchange Online: authentication, forwarding, inbox rules and audit
domain: m365
topic: exchange
source_url: https://learn.microsoft.com/exchange/clients-and-mobile-in-exchange-online/deprecation-of-basic-authentication-exchange-online
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Exchange Online (service, unversioned)
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [m365, exchange-online]
prerequisites: []
see_also: [https://learn.microsoft.com/defender-office-365/outbound-spam-policies-external-email-forwarding, https://learn.microsoft.com/purview/audit-mailboxes]
---

# Exchange Online security

## Authentication

- Basic authentication is retired for Exchange Online protocols (EWS, EAS, POP, IMAP, PowerShell, ...) except SMTP AUTH client submission, which Microsoft is retiring separately. Check whether SMTP AUTH is disabled at the organisation level (`Get-TransportConfig` `SmtpClientAuthenticationDisabled`) and enabled only on the mailboxes that need it.
- Conditional Access legacy-authentication blocks still matter: they stop attempts against any remaining legacy endpoints and give clean sign-in telemetry.

## External forwarding and inbox rules

- Attackers who take over a mailbox commonly create **inbox rules** that forward, redirect, delete or move messages (for example, rules that hide replies from the victim). ATT&CK: T1114.003 Email Forwarding Rule; T1564.008 Email Hiding Rules.
- **Automatic external forwarding** is governed by the outbound anti-spam policy's automatic forwarding setting. The secure default ("Automatic – System-controlled") blocks it. Remote domains and transport rules can also forward mail.
- Telemetry: unified audit log operations `New-InboxRule`, `Set-InboxRule`, `UpdateInboxRules`, `Set-Mailbox` (ForwardingSmtpAddress), and `New-TransportRule`.

## Mailbox auditing

Mailbox auditing is on by default for user mailboxes. `MailItemsAccessed` records mail reads (sync and bind) and is the key event for scoping mailbox data access. Check which audit tier the tenant's licences give, and how long logs are retained, before relying on it.

## Assessment procedure

1. SMTP AUTH status (organisation and per mailbox).
2. Outbound spam policy forwarding setting; transport rules with redirect or BCC actions; remote domain `AutoForwardEnabled`.
3. Inbox rules with forward/redirect to external addresses, or rules that move messages to obscure folders.
4. Audit enabled, `MailItemsAccessed` available, retention period.

## Common false positives

Forwarding to a documented journaling or archiving service; shared mailboxes with delegated access (that is permissions, not forwarding).
