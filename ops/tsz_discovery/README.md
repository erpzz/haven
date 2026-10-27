# Trusted Slink Zone — passive discovery and enrollment controllers

**Status: implementation candidate; independent runtime acceptance still required.** Python standard library only. Does not contact remote devices, open network sockets, install anything, invoke SSH, or change any live Haven services.

## Controller boundary

1. **Discovery** reads the local OS neighbor cache on explicitly allowed interfaces: Linux via ip -j neigh show, macOS via arp -an. Stores previously unseen neighbors as UNVERIFIED in a private inventory. Neighbor/MAC sightings are neither authentication nor ownership proof, and cannot enumerate every network device.
2. **Approval** consumes an HMAC-SHA256 signed receipt from the user's external verification manager. The receipt must reference an observed candidate, a unique node ID, the SHA-256 fingerprint of its verified public key, fixed scopes and short expiry.
3. **Attestation** requires a separate signature from an independent attestor key after the operator's verifier has established device identity and key possession. The receipt is bound to the original approval nonce and matching key fingerprint.
4. **Planning** emits inert WAIT_FOR_AUTHORIZED_DEPLOYER items. No installer, SSH, model worker, or other remote operation runs as a result. The future deployer must independently enforce current authority and scope before making changes.
5. **Revocation** via an owner-signed receipt removes the node from future plan output. Runtime credential revocation and cancellation of existing jobs are not implemented.

The two raw HMAC keys are supplied by the operator's verification system as private files (mode 0600, 32+ bytes). The controller never generates, publishes or signs its own approvals. This HMAC integration authenticates the *verifier's decision*; it does not itself cryptographically attest physical hardware. A production trust boundary must isolate the issuer secrets from AI user-space workers.

## Local commands

Run from the repository root. Discover is passive (no ping, multicast or scanning) and stores data only under the owner's default ~/.local/state/haven-tsz directory (mode 0700; JSON file mode 0600).

    python3 ops/tsz_discovery/tsz_fleet.py discover --interface en0
    python3 ops/tsz_discovery/tsz_fleet.py inventory
    python3 ops/tsz_discovery/tsz_fleet.py plan
    python3 -m unittest discover -s ops/tsz_discovery/tests -v

On Slink use its actual interface from ip link; on Mac use the intended en* interface. An optional --state-dir path must precede the subcommand. Do not publish real local inventory or signed receipts to GitHub.

## External verification receipts

Both JSON receipts are canonicalized as Python json.dumps(payload_without_signature, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8'), then signed with HMAC-SHA256. Put its lowercase hex digest in signature. Expiry is epoch seconds; maximum accepted window is 24 hours. Nonces are 32–128 lowercase hexadecimal characters, unique across actions.

Approval fields: kind='tsz-approval-v1', candidate_id, node_id, device_key_sha256 (64 lowercase hex), scopes (subset of inventory/inference/engineering/training), expires_at, nonce, signature. Sign with the private OWNER approval key.
Attestation fields: kind='tsz-attestation-v1', node_id, device_key_sha256, approval_nonce (same nonce as approval), expires_at, nonce (fresh), signature. Sign with a distinct ATTESTOR key only *after* independent verification of key possession and management authority.
Revocation fields: kind='tsz-revocation-v1', node_id, device_key_sha256, expires_at, nonce (fresh), signature. Sign with the OWNER approval key.

    python3 ops/tsz_discovery/tsz_fleet.py approve --receipt /private/approval.json --verification-key /private/owner.key
    python3 ops/tsz_discovery/tsz_fleet.py attest --receipt /private/attestation.json --verification-key /private/attestor.key
    python3 ops/tsz_discovery/tsz_fleet.py plan

Unknown candidates never yield work orders; a signed approval alone never yields one either. An expired approval or attestation automatically ceases to yield work orders. Work orders are not instructions to contact any candidate by IP, and grant no administrator privileges.

## Integration and limitations

- The registry contains private identifiers, addresses, observations, scopes and approval references. It is deliberately local and must never be committed to this public repository.
- No active discovery, routed/VPN/MDM inventory, Bluetooth, key-possession challenge protocol, authenticated remote transport, auto-installer, scheduler, worker heartbeat, or agent spawning has been implemented.
- Repeating the same receipt cannot renew trust; separate fresh approval and attestation decisions must be issued for a new admission. Fully automated *approved* fleet deployment belongs in a later scoped deployer.
- The existing Haven Model Lab's private provider registry is not changed. That integration needs a dedicated trusted adapter and non-disruptive live acceptance.
- The tests use synthetic neighbors and receipts. The code is not evidence that real enrollment or network model sharding currently works.

## Next experiment

Have the owner verification manager produce a disposable candidate approval and separate attestation on an isolated test node, confirm the PLAN output, exercise negative tests for replay/expiry/revocation, then implement an independently authorized user-space deployer using current SSH/MDM trust. Keep Claude's Mac Computer worktree, active GPU jobs and existing inference credentials untouched.