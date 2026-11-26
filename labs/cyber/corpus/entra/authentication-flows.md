---
id: entra.ca.auth-flows
title: Authentication flows: device code and authentication transfer
domain: entra
topic: conditional-access
source_url: https://learn.microsoft.com/entra/identity/conditional-access/concept-authentication-flows
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Microsoft Graph v1.0 conditionalAccessAuthenticationFlows
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [entra-id]
prerequisites: []
see_also: [https://learn.microsoft.com/entra/identity/conditional-access/policy-block-authentication-flows]
---

# Authentication flows: device code and authentication transfer

## Device code flow

Lets a device without a browser (a TV, a CLI) sign in: the device shows a code, the user enters it at the device-login page on another device. Attackers abuse it for phishing: they start a flow, send the code to a victim, and receive the victim's tokens when the victim signs in (ATT&CK T1528). Because the victim authenticates on a genuine Microsoft page, MFA does not stop it.

## Conditional Access control

`conditions.authenticationFlows.transferMethods` can contain `deviceCodeFlow` and/or `authenticationTransfer`. A policy with that condition, all users, all apps and grant `block` stops the flow. Exclude a narrowly scoped group for devices that genuinely need it (e.g. meeting-room devices) and the emergency accounts.

## Assessment

1. Look for an enabled policy with `transferMethods` containing `deviceCodeFlow` and grant `block`.
2. Check scope (all users) and exclusions.
3. Corroborate with sign-in logs: `authenticationProtocol` = `deviceCode` shows who uses the flow today.

## False positives

Report-only policies with this condition do not block. Conversely, the flow can be absent from sign-in logs simply because nobody uses it; absence of usage is not a control.
