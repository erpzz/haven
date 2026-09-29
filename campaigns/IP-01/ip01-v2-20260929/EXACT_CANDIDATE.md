# Exact evaluated candidate reproduction

Exact Git commit: `0b59551f36990cfb8a723f97da6d367358a8ceb5`. Historical evaluation recorded `487c67299445a29e0fbbdede04259565f741f587` plus the 37 per-file worktree hashes in receipts/FINAL_CANDIDATE_01.json. The historical Git blobs normalized some line endings and alone did not reproduce those bytes.

No evaluated worktree byte changed. This commit materializes all 37 exact byte sequences as Git blobs. Root verified every blob and every member produced by:

```powershell
git -c core.autocrlf=false archive --format=tar --output=ip01-evaluated.tar 0b59551f36990cfb8a723f97da6d367358a8ceb5 labs/ip01
```

Extract the archive into a new operator-selected directory. Ordinary checkout may apply local line-ending settings; the archive is the exact-byte reproduction route. All 37 SHA256 values and blob IDs are in receipts/EXACT_CANDIDATE_RECONCILIATION.json. The archive SHA256 is `4a58860528135a89e67ed4fee4b74296be287d46d8f700600e47cf52a81f8d12`.

This is byte identity evidence, not another execution or independent review. Original source freeze and QA evidence remain untouched. Final execution is PARTIAL and retains all observed failures.
