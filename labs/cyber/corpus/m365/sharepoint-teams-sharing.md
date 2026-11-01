---
id: m365.sharing
title: SharePoint, OneDrive and Teams external sharing
domain: m365
topic: collaboration
source_url: https://learn.microsoft.com/sharepoint/turn-external-sharing-on-or-off
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: SharePoint Online / Microsoft Teams (service, unversioned)
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [m365, sharepoint-online, onedrive, teams]
prerequisites: []
see_also: [https://learn.microsoft.com/microsoftteams/communicate-with-users-from-other-organizations]
---

# SharePoint, OneDrive and Teams external sharing

## Sharing levels

Organisation-wide levels, from most to least permissive:
1. **Anyone** (unauthenticated links);
2. **New and existing guests**;
3. **Existing guests**;
4. **Only people in your organization**.

A site's setting can be equal to or **more restrictive** than the organisation's, never less. OneDrive has its own level, also capped by the organisation's.

## Settings that change exposure

- **Anyone links**: expiry days, and whether they can grant edit or only view. Unauthenticated links can be forwarded, and access by them is not tied to an identity.
- **Default link type** (specific people / organisation / anyone) shapes what users actually send.
- Domain allow/deny lists for sharing; guest access expiration; whether guests must sign in with the same account the invitation was sent to.
- Sensitivity labels with site-level sharing controls, and DLP policies for sensitive content.

## Teams

- **External access (federation)** lets users chat and meet with other organisations' users, who are not added to your directory.
- **Guest access** adds guests to teams and channels.
- Both are configurable per domain. Guests reach team files through SharePoint, so the SharePoint sharing level caps them.

## Assessment procedure

1. Organisation and OneDrive sharing levels; sites set more permissively than intended (e.g. HR or finance sites allowing guests).
2. Anyone-link expiry and permissions; the default link type.
3. Guest inventory: stale guests, guests in privileged roles or groups (cross-check the Entra role assignments).
4. Teams external access and guest settings against the organisation's collaboration policy.

## Common false positive

A public-facing communication site intentionally using Anyone links, documented and labelled.
