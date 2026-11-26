---
id: general.tool-failures
title: Recovering from tool and API failures without inventing results
domain: general
topic: tool-use
source_url: https://learn.microsoft.com/graph/throttling
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Microsoft Graph v1.0; Azure CLI 2.x
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [microsoft-graph, azure-cli, shell]
prerequisites: []
see_also: [https://learn.microsoft.com/graph/aad-advanced-queries, https://learn.microsoft.com/entra/identity-platform/reference-error-codes]
---

# Recovering from tool and API failures

## General procedure

1. Read the actual error. Classify it: missing tool, wrong syntax, authentication, authorization, throttling, timeout, not found, unsupported query.
2. Fix the cause or report it. Do **not** continue as if the command succeeded, and never invent its output.
3. Retry only retryable errors (throttling, transient 5xx, timeouts), with backoff.
4. If a capability is missing (tool not installed, no permission), say what is missing and what would be needed.

## Shell

- `command not found` / exit code 127: the tool is not installed or not on PATH. Check with `command -v`. Use an available alternative (`ss` vs `netstat`, `ip` vs `ifconfig`) or report.
- Exit code 126: found but not executable (permissions).
- `Permission denied`: needs elevated rights; do not escalate without authorization.

## Microsoft Graph

- `429 Too Many Requests`: throttled. Wait for the `Retry-After` header (seconds), then retry.
- `401 InvalidAuthenticationToken`: token missing, expired or for the wrong audience (must be `https://graph.microsoft.com`).
- `403 Authorization_RequestDenied`: authenticated but lacking a permission or role.
- `400` "Request_UnsupportedQuery" or an error about `$count`/`$search`/`endsWith`: advanced query capabilities need the header `ConsistencyLevel: eventual` **and** `$count=true` on directory objects.
- `404 Request_ResourceNotFound`: wrong id, or the object was deleted (check `/directory/deletedItems`).

## Azure CLI and ARM

- `AADSTS50076` / `AADSTS50079`: MFA is required or must be registered; re-run `az login` interactively. Not a permission problem.
- `AADSTS700016`: application id not found in the tenant (wrong tenant or app not consented).
- `AuthorizationFailed` from ARM: the identity lacks the action at that scope; the message names the action and scope.
- `SubscriptionNotFound`: wrong subscription context (`az account show`, `az account set`).
