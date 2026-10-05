"""Real Chromium / local application integration; inference is a labelled test double.

Does not download a browser, model or runtime. Requires developer-provided Playwright
and Chromium. Outputs screenshots and a JSON execution receipt in artifacts/.
"""
from pathlib import Path
import json, os, shutil, sys, tempfile, threading, time
from urllib.parse import urlsplit
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labcore import Lab
from server import Server
from fake_backend import FakeBackend
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts';OUT.mkdir(exist_ok=True)
checks=[];errors=[];external=[]
started=time.time()
with tempfile.TemporaryDirectory(prefix='haven-browser-') as t:
    lab=Lab(Path(t));backend=server=thread=browser=None
    try:
      backend=FakeBackend();server=Server(('127.0.0.1',0),lab)
      thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
      url=f'http://127.0.0.1:{server.server_port}/#token={lab.token}'
      with sync_playwright() as p:
        chromium=os.environ.get('HAVEN_TEST_CHROMIUM') or shutil.which('chromium') or shutil.which('chromium-browser') or (p.chromium.executable_path if Path(p.chromium.executable_path).is_file() else None)
        if not chromium:raise SystemExit('Provide HAVEN_TEST_CHROMIUM; no automatic browser download.')
        browser=p.chromium.launch(executable_path=chromium,headless=True,chromium_sandbox=True)
        context=browser.new_context(viewport={'width':1440,'height':1000},device_scale_factor=1)
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r: external.append(r.url) if urlsplit(r.url).hostname not in ('127.0.0.1',None) else None)
        try:
            page.goto(url);expect(page.locator('#active-model')).to_have_text('No model loaded')
            gpu_label=lab.hw['gpus'][0]['name'] if lab.hw['gpus'] else 'GPU telemetry'
            expect(page.locator('#gpu-name')).to_contain_text(gpu_label)
            assert '#token=' not in page.url
            assert page.locator('#send').is_disabled()
            checks.append('Offline startup: token removed from URL, actual GPU status observed, send disabled')
            page.screenshot(path=str(OUT/'desktop-offline.png'),full_page=True)
            page.locator('[data-view="models"]').click();expect(page.locator('.model-card')).to_have_count(4)
            page.once('dialog',lambda d:d.dismiss());page.locator('.model-card button').first.click()
            assert not lab.jobs
            checks.append('Four catalog models; declining download causes zero download jobs')
            page.screenshot(path=str(OUT/'model-library.png'),full_page=True)
            page.locator('#import-model').click();page.locator('#import-path').fill(str(Path(t)/'missing.gguf'))
            page.locator('#confirm-import').click();expect(page.locator('#import-dialog')).to_be_visible()
            page.locator('#import-dialog button[value="cancel"]').click()
            checks.append('Invalid local GGUF path rejected through real form')
            page.locator('[data-view="setup"]').click();page.locator('#endpoint').fill(backend.base)
            page.locator('#connect').click();expect(page.locator('#active-model')).to_have_text('TEST_DOUBLE-not-a-real-model')
            page.locator('#prompt').fill('Synthetic browser test. No real inference.');page.locator('#send').click()
            expect(page.locator('.result-meta').last).to_contain_text('COMPLETED',timeout=10000)
            expect(page.locator('.assistant .body').last).to_contain_text('Unicode: café ✓.')
            assert len(backend.requests)==1
            checks.append('Actual form -> local HTTP -> synthetic SSE stream -> Unicode rendered once with metrics')
            page.screenshot(path=str(OUT/'chat-test-double.png'),full_page=True)
            assert page.locator('#max-tokens').input_value() == '2048'
            backend.finish_reason='length';page.locator('#prompt').fill('Synthetic output-limit test');page.locator('#send').click()
            expect(page.locator('.result-meta').last).to_contain_text('OUTPUT LIMIT REACHED',timeout=10000)
            expect(page.locator('.continue-generation').last).to_be_visible()
            assert backend.requests[-1]['max_tokens'] == 2048
            backend.finish_reason='stop';page.locator('.continue-generation').last.click()
            expect(page.locator('.result-meta').last).to_contain_text('COMPLETED',timeout=10000)
            continuation_messages=backend.requests[-1]['messages']
            assert continuation_messages[-2]['role']=='assistant'
            assert continuation_messages[-1]['role']=='user' and 'Continue exactly where you stopped' in continuation_messages[-1]['content']
            assert len(backend.requests)==3
            checks.append('Output-limit finish reason is surfaced; Continue preserves partial assistant context and resumes without a visible fake user turn')
            backend.slow=True;page.locator('#prompt').fill('Cancel this synthetic response');page.locator('#send').click()
            expect(page.locator('.assistant .body')).to_have_count(4)
            expect(page.locator('.assistant .body').nth(3)).to_contain_text('This is')
            page.locator('#cancel').click();expect(page.locator('.result-meta').last).to_contain_text('STOPPED',timeout=10000)
            backend.slow=False;checks.append('Real browser cancellation preserves partial output and records uncertainty')
            original_settings = {'temperature':float(page.locator('#temperature').input_value()),
                                 'max_tokens':int(page.locator('#max-tokens').input_value()),
                                 'seed':int(page.locator('#seed').input_value())}
            page.locator('[data-view="experiments"]').click();page.locator('#bench-repeats').select_option('3')
            page.locator('#bench-label').fill('TEST DOUBLE · browser integration, not GPU performance')
            backend.slow=True
            page.once('dialog',lambda d:d.accept());page.locator('#run-bench').click()
            expect(page.locator('#connect')).to_be_disabled();expect(page.locator('#unload')).to_be_disabled()
            page.locator('#bench-label').fill('Changed after start')
            page.locator('#bench-workload').select_option('code')
            page.locator('[data-view="playground"]').click()
            page.locator('#temperature').fill('1');page.locator('#max-tokens').fill('128');page.locator('#seed').fill('7')
            page.locator('[data-view="experiments"]').click()
            expect(page.locator('#bench-status')).to_contain_text('Finished.',timeout=20000)
            backend.slow=False
            expect(page.locator('#bench-table tr')).to_have_count(3)
            rows=[json.loads(x) for x in (Path(t)/'benchmarks.jsonl').read_text(encoding='utf-8').splitlines()]
            assert all(x['test_double'] for x in rows) and len(rows)==3
            assert len({x['prompt_sha256'] for x in rows})==1
            assert all(x['label'].startswith('TEST DOUBLE · browser integration') for x in rows)
            assert all(all(x['settings'][k]==v for k,v in original_settings.items()) for x in rows)
            assert len(backend.requests)==7
            checks.append('Three explicit benchmark repetitions, three durable TEST_DOUBLE records, no extra warmup')
            checks.append('Benchmark retains initial workload/label/settings despite edited controls; backend controls locked')
            with page.expect_download() as event:page.locator('#export-bench').click()
            exported=event.value;exported.save_as(str(OUT/'test-double-benchmarks.json'))
            checks.append('Actual result export download from browser')
            page.locator('[data-view="research"]').click();expect(page.locator('#research-text')).to_contain_text('HYPOTHESES',timeout=10000)
            page.locator('[data-view="setup"]').click();page.locator('#disconnect').click()
            page.locator('[data-view="playground"]').click();expect(page.locator('#active-model')).to_have_text('No model loaded')
            assert backend.thread.is_alive()
            checks.append('Disconnect leaves externally attached fixture service running')
            page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(OUT/'mobile-offline.png'),full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1')
            checks.append('390px mobile layout: no horizontal document overflow')
            assert not errors,errors
            assert not external,external
            checks.append('No browser page errors and no external browser requests observed')
        finally:
            browser.close();browser=None
    finally:
        if browser is not None:
            try: browser.close()
            except Exception: pass
        if server is not None:
            if thread is not None: server.shutdown();thread.join(3)
            server.server_close()
        lab.shutdown()
        if backend is not None: backend.close()
    receipt={'status':'PASS','checks':checks,'elapsed_seconds':round(time.time()-started,3),'page_errors':errors,
      'external_browser_requests':external,'inference':'TEST_DOUBLE_ONLY','real_model_calls':0,'gpu_benchmarks':0,
      'platform':sys.platform,'browser':'Chromium through Playwright with sandbox enabled','services_stopped':not thread.is_alive() and not backend.thread.is_alive(),
      'limitations':['This fixture does not execute bootstrap or an owned model engine','Real NVIDIA/model inference is measured separately','Root-produced browser testing, not independent review']}
    (OUT/'browser-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))
