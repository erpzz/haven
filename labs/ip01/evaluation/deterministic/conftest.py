import os,sys,hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from common import SNAP,Actor,write
sys.dont_write_bytecode=True;sys.path.insert(0,str(SNAP/'labs/ip01'))
from haven.app import create_app

@pytest.fixture
def lab(request):
    runtime=SNAP/'.ip01-runtime'/'qa-e2e'/os.environ['QA_RUN_ID']/hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:12]
    app=create_app(runtime_dir=runtime)
    with TestClient(app,base_url='http://127.0.0.1:8766') as first:
        # Second TestClient shares this lifespan/app, but has an independent cookie jar.
        second=TestClient(app,base_url='http://127.0.0.1:8766')
        second.portal=first.portal
        a,b=Actor(first,'A'),Actor(second,'B')
        assert first.cookies!=second.cookies
        assert app.state.service.model_gate() is None
        value={'app':app,'a':a,'b':b,'store':app.state.store,'runtime':runtime,'first':first,'second':second}
        try:yield value
        finally:
            second.close()
            write(Path(os.environ['QA_RUN_DIR'])/(request.node.name.replace('/','_')+'-runtime.json'),{'runtime':str(runtime),'store':str(app.state.store.path),'gate_absent':app.state.service.model_gate() is None})
