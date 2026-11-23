"""Standard-library runner with individual test IDs, times and source hashes."""
import argparse
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import unittest
from uuid import uuid4

ROOT=Path(__file__).resolve().parent

def stamp():return datetime.now(timezone.utc).isoformat()

class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.rows=[];self.starts={}
    def startTest(self,test):
        super().startTest(test);self.starts[test.id()]=(stamp(),time.monotonic())
    def record(self,test,status,detail=None):
        start,mono=self.starts.get(test.id(),(stamp(),time.monotonic()))
        self.rows.append({"id":test.id(),"status":status,"started_at":start,"ended_at":stamp(),
                          "elapsed_seconds":round(time.monotonic()-mono,6),"detail":detail})
    def addSuccess(self,test):super().addSuccess(test);self.record(test,"EXECUTED_PASS")
    def addFailure(self,test,err):super().addFailure(test,err);self.record(test,"EXECUTED_FAIL",self._exc_info_to_string(err,test))
    def addError(self,test,err):super().addError(test,err);self.record(test,"EXECUTED_FAIL",self._exc_info_to_string(err,test))
    def addSubTest(self,test,subtest,err):
        super().addSubTest(test,subtest,err)
        if err:self.record(subtest,"EXECUTED_FAIL",self._exc_info_to_string(err,test))
    def addSkip(self,test,reason):super().addSkip(test,reason);self.record(test,"SKIPPED",reason)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('suite',choices=['n1','n2','all']);args=parser.parse_args()
    if sys.version_info[:2]!=(3,12):parser.error('Python 3.12 required')
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_*.py' if args.suite=='all' else f'test_{args.suite}.py')
    stream=io.StringIO();start=stamp()
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
    record={"label":"TEST DOUBLE / NOT LIVE AI","scope":"SYNTHETIC_LAB_ONLY","suite":args.suite,
            "command":[sys.executable,'-B','run_checks.py',args.suite],"started_at":start,"ended_at":stamp(),
            "exit_code":0 if result.wasSuccessful() else 1,"tests_run":result.testsRun,
            "failures":len(result.failures),"errors":len(result.errors),"skips":len(result.skipped),
            "tests":result.rows,"log":stream.getvalue(),
            "source_sha256":{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                              for folder in ['haven_lab','tests','fixtures'] for p in sorted((ROOT/folder).glob('*')) if p.is_file()}}
    directory=ROOT.parent/'outputs/logs';directory.mkdir(exist_ok=True)
    path=directory/(args.suite+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:6]+'.json')
    path.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({"result":str(path),"exit_code":record['exit_code'],"tests_run":result.testsRun,"failures":record['failures'],"errors":record['errors']}))
    if not result.wasSuccessful():print(stream.getvalue(),file=sys.stderr)
    return record['exit_code']

if __name__=='__main__':raise SystemExit(main())
