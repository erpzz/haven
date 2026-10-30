"""Pick the 12 fixed COT-EFF-1 prompts from the secpatch dev eval: first 6 root_cause and first 6 remediate, file order."""
import json
import sys

rows = [json.loads(x) for x in open(sys.argv[1])]
assert all(r['split'] == 'dev' for r in rows), 'dev split only; held-out items are never used for speed tests'
pick = [r for r in rows if r['task'] == 'root_cause'][:6] + [r for r in rows if r['task'] == 'remediate'][:6]
for r in pick:
    print(json.dumps({'id': r['id'], 'task': r['task'], 'messages': r['messages']}))
