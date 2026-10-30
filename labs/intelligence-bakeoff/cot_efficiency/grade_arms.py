"""Grade COT-EFF answers with the secpatch graders and compute seconds per correct answer per arm."""
import json
import pathlib
import sys

SECPATCH = pathlib.Path.home() / '.local/state/haven-secpatch/code-v4/secpatch'
sys.path.insert(0, str(SECPATCH))
from evaluate import grade  # noqa: E402

run, prompts_path = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
bandit = sys.argv[3] if len(sys.argv) > 3 else 'bandit'
items = {p['id']: p for p in map(json.loads, prompts_path.read_text().splitlines())}
out, base = [], None
for arm_dir in sorted(d for d in run.iterdir() if (d / 'rows.jsonl').exists()):
    rows = [json.loads(x) for x in (arm_dir / 'rows.jsonl').read_text().splitlines()]
    if not rows:
        continue
    correct = sum(grade(items[r['prompt']], r['answer'], bandit)['score'] for r in rows)
    wall = sum(r['wall_s'] + r.get('followup_wall_s', 0) for r in rows)
    row = {'arm': arm_dir.name, 'correct': f'{correct}/{len(rows)}', 'wall_s': round(wall, 1),
           's_per_correct': round(wall / correct, 1) if correct else None,
           'turn2_mean_s': round(sum(r.get('followup_wall_s', 0) for r in rows) / len(rows), 2),
           'turn2_mean_prompt_tokens_processed': round(sum(r.get('followup_prompt_n') or 0 for r in rows) / len(rows))}
    out.append(row)
    if arm_dir.name == 'A0':
        base = row
for row in out:
    row['realworld_multiplier'] = round(base['s_per_correct'] / row['s_per_correct'], 2) \
        if base and base['s_per_correct'] and row['s_per_correct'] else None
    print(json.dumps(row))
(run / 'graded.json').write_text(json.dumps(out, indent=1))
