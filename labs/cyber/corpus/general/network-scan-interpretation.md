---
id: general.network-scan
title: Interpreting network scan results
domain: network
topic: scanning
source_url: https://nmap.org/book/man-port-scanning-basics.html
source_org: Nmap
published: null
retrieved: 2026-10-31
product_version: Nmap 7.x reference guide
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [nmap, tls]
prerequisites: []
see_also: [https://nmap.org/book/man-version-detection.html]
---

# Interpreting network scan results

## Port states (Nmap)

- `open`: an application accepted the connection or replied.
- `closed`: reachable host, nothing listening (TCP RST). The host is up.
- `filtered`: no answer or an ICMP unreachable; a firewall is dropping probes. It is **not** evidence of a service.
- `open|filtered` (UDP, some scan types): cannot tell; needs a protocol-specific probe.
- `unfiltered`: reachable, open/closed unknown (ACK scan).

## Service and version detection

- The `SERVICE` column without `-sV` is only the IANA name for the port number, not what is running.
- `-sV` versions come from banners and probe responses. Banners can be changed, hidden or reflect a proxy or load balancer in front.
- Distribution packages **backport** security fixes without changing the upstream version string: a distribution build such as `OpenSSH 9.6p1 Ubuntu-3ubuntu13.x` may already contain fixes for CVEs that "affect 9.6". A version-only CVE match is a lead with low confidence; confirm with the package changelog/advisory (e.g. Ubuntu USN, Debian DSA) or an authenticated package check.
- `ssl/http` on 443 with a self-signed certificate is common for appliance management interfaces; the certificate subject often names the product.

## Scope discipline

Scan only targets explicitly in scope; record the source host, time and command. A scan from inside the network does not show internet exposure, and vice versa.
