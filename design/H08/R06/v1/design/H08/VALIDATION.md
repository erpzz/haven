# R06 documentation verification

Executed 2026-09-28 UTC using Python 3.12 and the standard library. This is documentation/package verification, not a sensor experiment, independent research replication, schema implementation, or M0 test.

The checker below compares both input ZIPs with their extracted files; verifies the actual starter-template structure, ten requirement mappings, 22 source IDs, internal links, summary length, JSON syntax, status labels and documentation-only file types. Results are in [VALIDATION.json](VALIDATION.json). All RF acceptance and proposed experiment states remain NOT_EXECUTED. H00/H04/H06 review remains pending.

The summary is 463 words and supplied as one-page-length Markdown; no paginated document or UI rendering is claimed. Source URLs were reviewed during research as described in EVIDENCE_REGISTER; this checker does not browse or infer that every URL remains available.

## Executed verification command

```bash
python3 /workspace/scratch/ba074ae35c94/work/validate_r06_handback.py
```

The temporary checker is reproduced below so its scope is inspectable. It is packaging tooling, not a future Haven coding package. Paths can be adjusted in another environment. The delivery SHA-256 manifest is produced after these results are written; the ZIP is separately checked for CRC errors and byte-for-byte agreement with those manifest entries.

A preliminary fence check counted a literal delimiter inside its own reproduced source. The final check counts fence lines instead; this was a validator correction, not a change to any Haven code.

## Checker source

```python
from pathlib import Path
import hashlib, json, platform, re, sys, zipfile

workspace = Path('/workspace/scratch/ba074ae35c94')
package = workspace / 'deliverables/HAVEN_R06_RF_Spatial_Handback_v1'
design = package / 'design/H08'
checks = []

def record(name, passed, detail):
    checks.append({'check_id': name, 'status': 'EXECUTED_PASS' if passed else 'EXECUTED_FAIL', 'detail': detail})

inputs = json.loads((design / 'INPUT_AUDIT.json').read_text())
for archived in inputs['archives']:
    dirname = 'inputs' if archived['kind'] == 'starter' else 'upload'
    extracted = workspace / ('starter' if archived['kind'] == 'starter' else 'prompt_pack')
    archive = workspace / dirname / archived['archive_name']
    matches = hashlib.sha256(archive.read_bytes()).hexdigest() == archived['sha256']
    with zipfile.ZipFile(archive) as z:
        for row in archived['inventory']:
            data = z.read(row['path'])
            matches &= data == (extracted / row['path']).read_bytes()
            matches &= hashlib.sha256(data).hexdigest() == row['sha256']
    record('DOC-INPUT-' + archived['kind'].upper(), bool(matches), {'files_compared': len(archived['inventory']), 'archive_sha256': archived['sha256']})

required = {'START_HERE.md','CURRENT_STATUS.md','PRECEDENCE.md','scope/COVERAGE.md','docs/06_WIRELESS_SPATIAL_RESEARCH.md','research/RESEARCH_ATLAS.md','contracts/README.md','agents/HANDOFF_TEMPLATE.md'}
record('DOC-CONTEXT', required == {r['path'] for r in inputs['required_context_read']}, 'Eight required context files have read records and hashes; reading itself is author-reported.')

handoff = (design / 'R06_HANDOFF.md').read_text()
headings = ['# Specialist handback','## Decisions','## Evidence','## Interface changes','## Acceptance','## Risks and open questions','## Next package']
actual_headings = [line for line in handoff.splitlines() if re.match(r'^#{1,2} ',line)]
fields = ['Thread / owner / task ID:', 'Input repository version and hashes:', 'Requirements covered (retain IDs):', 'Actual work performed versus proposed:', 'Owned paths changed:']
record('DOC-TEMPLATE', actual_headings == headings and all(f in handoff for f in fields), 'Uses actual starter handoff headings and all five header fields.')

coverage = (design / 'INTEGRATION_AND_PACKAGES.md').read_text()
covered = all(f'REQ-RF-{i:02}' in coverage and f'AT-RF-{i:02}' in coverage for i in range(1,11))
record('DOC-COVERAGE', covered, 'Ten RF requirement/acceptance mappings retained; operational status NOT_EXECUTED.')

markdown = sorted(package.rglob('*.md'))
missing = []
local_count = 0
for path in markdown:
    for target in re.findall(r'\[[^\]\n]+\]\(([^)]+)\)', path.read_text()):
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
            continue
        local_count += 1
        resolved = (path.parent / target.split('#',1)[0]).resolve()
        if not resolved.is_file() or not resolved.is_relative_to(package.resolve()):
            missing.append({'file': str(path.relative_to(package)), 'target': target})
record('DOC-LINKS', not missing, {'internal_links':local_count,'missing_or_external_paths':missing, 'web_links':'Not live link-tested by this validator; source access is recorded separately.'})

source_text = (design / 'EVIDENCE_REGISTER.md').read_text()
source_ids = set(re.findall(r'^### (R06-S\d{2})',source_text,re.M))
referenced = set()
for p in markdown:
    referenced |= set(re.findall(r'R06-S\d{2}',p.read_text()))
expected_ids = {f'R06-S{i:02}' for i in range(1,23)}
record('DOC-SOURCES',source_ids == expected_ids and referenced <= source_ids, {'source_records':len(source_ids),'unresolved_ids':sorted(referenced-source_ids)})

summary_words = len((design/'INTEGRATION_SUMMARY.md').read_text().split())
record('DOC-SUMMARY',400 <= summary_words <= 550, {'words':summary_words,'format':'One-page-length Markdown, not a paginated PDF.'})

experiments = (design/'EXPERIMENTS.md').read_text()
record('DOC-STATUS','All experiments below: PROPOSED_NOT_EXECUTED' in experiments and 'NOT_EXECUTED' in handoff and 'not accepted or qualified' in handoff,'Status labels present; no experimental performance validated.')

json_errors = []
for p in package.rglob('*.json'):
    try: json.loads(p.read_text())
    except (ValueError,UnicodeError) as e: json_errors.append(str(p.relative_to(package))+': '+str(e))
record('DOC-JSON',not json_errors,{'errors':json_errors})

unexpected = [str(p.relative_to(package)) for p in package.rglob('*') if p.is_file() and p.suffix not in {'.md','.json','.sha256'}]
record('DOC-NO-IMPLEMENTATION',not unexpected,{'unexpected_file_types':unexpected,'scope':'This checks delivery file types, not application correctness.'})
record('DOC-FENCES',all(sum(1 for line in p.read_text().splitlines() if line.startswith('```')) % 2 == 0 for p in markdown),'Markdown code fences balanced; Mermaid/browser rendering not executed.')

result = {'task_id':'R06-DESIGN-001','validation_scope':'DOCUMENTATION_AND_INPUT_INTEGRITY_ONLY','date_utc':'2026-09-28','command':'python3 /workspace/scratch/ba074ae35c94/work/validate_r06_handback.py','environment':{'python':sys.version.split()[0],'os':platform.system(),'kernel':platform.release()},'checks':checks,'all_document_checks_passed':all(x['status']=='EXECUTED_PASS' for x in checks),'rf_acceptance':{f'AT-RF-{i:02}':'NOT_EXECUTED' for i in range(1,11)},'experiments':{f'R06-E{i}':'PROPOSED_NOT_EXECUTED' for i in range(6)},'m0_tests':'NOT_EXECUTED','hardware_native_physical_tests':'NOT_EXECUTED','independent_review':'PENDING_H00_H04_H06'}
(design/'VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'checks':len(checks),'all_document_checks_passed':result['all_document_checks_passed'],'internal_links':local_count,'summary_words':summary_words,'source_records':len(source_ids),'failures':[c for c in checks if c['status']=='EXECUTED_FAIL']},indent=2))
if not result['all_document_checks_passed']: raise SystemExit(1)
```
