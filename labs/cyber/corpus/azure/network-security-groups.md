---
id: azure.network.nsg
title: Network security groups: rule evaluation and exposure analysis
domain: azure
topic: network
source_url: https://learn.microsoft.com/azure/virtual-network/network-security-group-how-it-works
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Azure Resource Manager Microsoft.Network 2024-05-01
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [azure, networking]
prerequisites: []
see_also: [https://learn.microsoft.com/azure/virtual-network/network-security-groups-overview]
---

# Network security groups

## Rule evaluation

- Rules have a priority from 100 to 4096; **lower numbers are evaluated first** and processing stops at the first match.
- Default rules (cannot be deleted, lowest precedence): inbound 65000 AllowVnetInBound, 65001 AllowAzureLoadBalancerInBound, 65500 DenyAllInBound; outbound 65000 AllowVnetOutBound, 65001 AllowInternetOutBound, 65500 DenyAllOutBound.
- An NSG can be attached to a subnet and to a NIC. For inbound traffic the subnet NSG is evaluated first, then the NIC NSG; **both must allow** it. For outbound the order is reversed.
- Security rules are stateful: return traffic for an allowed flow is permitted.
- Source `*`, `0.0.0.0/0`, `Internet` or `Any` from the internet are equivalent for exposure.

## Is a VM really exposed?

Internet exposure needs: a public IP (or a load balancer / NAT rule) reaching the NIC, **and** an allow rule in every NSG in the path that matches the port before any deny. A permissive rule for 3389 in a NIC NSG is not exposure if the subnet NSG denies 3389 at a lower priority number, or if the VM has no public path. Use effective security rules and Network Watcher IP flow verify to confirm.

## High-risk patterns

Inbound allow from the internet to management ports 22 (SSH), 3389 (RDP), 5985/5986 (WinRM), databases 1433/3306/5432, or all ports. Prefer Azure Bastion or just-in-time VM access.
