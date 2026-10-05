"""Offline, in-memory layout inspection ONLY; does not navigate to a server.

Separate from browser_smoke.py. A render is NOT evidence of live UI/API integration.
No network requests or model inference. Requires existing Playwright/system Chromium.
"""
import json,re,shutil,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts';OUT.mkdir(exist_ok=True)
html=(ROOT/'static/index.html').read_text()
html=re.sub(r'<script.*?</script>','',html,flags=re.S)
html=re.sub(r'<link[^>]+>','',html)
html=re.sub(r'<img[^>]+>', '<span class="offline-icon" aria-hidden="true">◈</span>',html)
style=(ROOT/'static/style.css').read_text()
html=html.replace('</head>','<style>'+style+'</style></head>')
requests=[];errors=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
    try:
        page=b.new_page(viewport={'width':1440,'height':1000})
        page.on('request',lambda r:requests.append(r.url));page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(html)
        page.locator('#connection-pill').evaluate("n=>n.textContent='OFFLINE LAYOUT PREVIEW · NOT LIVE INFERENCE'")
        page.screenshot(path=str(OUT/'desktop-layout.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1')
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(OUT/'mobile-layout.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1')
        assert not requests and not errors
        receipt={'status':'PASS_STATIC_LAYOUT_ONLY','viewports':[{'width':1440,'height':1000},{'width':390,'height':844}],
          'horizontal_overflow':False,'requests':requests,'page_errors':errors,'navigation':'NOT_PERFORMED',
          'live_browser_integration':'BLOCKED_BY_BROWSER_ADMINISTRATOR; see browser_smoke failure',
          'inference':'NOT_EXECUTED','browser_closed':True}
    finally:b.close()
(OUT/'layout-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
