"""Copy this harness outside candidate source before running. All writes local to harness."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--smoke',action='store_true');args=p.parse_args()
base=Path(__file__).resolve().parent;source=args.candidate.resolve()
if base.is_relative_to(source):raise SystemExit('Copy reviewed harness to an evaluator directory outside candidate source before running')
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');snap=base/'snapshots'/stamp/'candidate';files={}
for relative in [*[x.relative_to(source) for x in (source/'labs/ip01/haven').rglob('*') if x.is_file() and '__pycache__' not in x.parts],Path('labs/ip01/scripts/run.py'),Path('labs/ip01/requirements.lock')]:
    raw=(source/relative).read_bytes();destination=snap/relative;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw);assert raw==(source/relative).read_bytes();files[relative.as_posix()]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
(base/'selected.json').write_text(json.dumps({'snapshot':str(snap),'source':str(source),'files':files,'model_gate':'ABSENT','assignment':'USER-ALLOCATED-DEVELOPMENT'},indent=2))
run=base/'runs'/stamp;run.mkdir(parents=True);env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',QA_RUN_ID=stamp,QA_RUN_DIR=str(run),TMP=str(run),TEMP=str(run))
tests=['test_functional.py::test_private_useful_B_forbidden_and_explicit_shared','test_functional.py::test_one_use_at_zero_duplicate_and_no_refund'] if args.smoke else ['test_functional.py','test_backing.py','test_static_domains.py','test_bounds.py','test_code_early.py','test_extra_bounds.py']
cmd=[sys.executable,'-B','-m','pytest',*[str(base/t) for t in tests],'-q','-p','no:cacheprovider','--basetemp',str(run/'tmp'),'--junitxml',str(run/'junit.xml')]
with (run/'stdout.txt').open('w') as out,(run/'stderr.txt').open('w') as err:result=subprocess.run(cmd,cwd=base,env=env,stdout=out,stderr=err,timeout=240)
after={r:hashlib.sha256((source/r).read_bytes()).hexdigest() for r in files};stable=all(after[r]==files[r]['sha256'] for r in files)
receipt={'command':cmd,'exit_code':result.returncode,'candidate_files':files,'source_unchanged':stable,'real_model_calls':0,'final_suite_starts':0,'smoke':args.smoke,'vector_denominator':104,'scope':'Private source copy; deterministic development only. Static domains use explicit in-memory constant faults, not HTTP reconfiguration.'}
(run/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({'exit_code':result.returncode,'source_unchanged':stable,'run':str(run),'stdout':(run/'stdout.txt').read_text()}));sys.exit(result.returncode if stable else 2)
