"""Author browser development evidence, using a separately owned local server.

Run with provisioned Playwright and PLAYWRIGHT_BROWSERS_PATH in private runtime.
No model inference. Server start/stop is owned separately by root's launcher.
"""
from pathlib import Path
import json
import sys
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[4]
ARTIFACTS=ROOT/'.ip01-runtime'/'app-dev'/(sys.argv[1] if len(sys.argv)>1 else 'browser')
ARTIFACTS.mkdir(parents=True,exist_ok=True)
owner=json.loads((ARTIFACTS/'control'/'app-owner.json').read_text())
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    try:
        a=browser.new_context(viewport={'width':1440,'height':1100})
        b=browser.new_context(viewport={'width':1440,'height':1100})
        pa,pb=a.new_page(),b.new_page()
        for page in (pa,pb):
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('console',lambda message:errors.append(message.text) if message.type=='error' else None)
            response=page.goto(owner['url'])
            assert response.status==200
        pa.locator('[data-person="A"]').click(); pb.locator('[data-person="B"]').click()
        expect(pa.locator('#identity')).to_have_text('Person A')
        expect(pb.locator('#identity')).to_have_text('Person B')
        pa.get_by_role('button',name='Add a note',exact=True).click()
        pa.locator('#note-title').fill('Weekend at Pine Lake')
        pa.locator('#note-text').fill('Meet at Pine Lake at 9 on Saturday. Pack water, a rain jacket, and sandwiches for the lakeside walk.')
        pa.get_by_role('button',name='Save note',exact=True).click()
        expect(pa.locator('.note-card')).to_have_count(1)
        expect(pb.locator('.note-card')).to_have_count(0)
        pa.get_by_role('button',name='Share',exact=True).click()
        pa.locator('#share-uses').select_option('5')
        pa.get_by_role('button',name='Approve sharing',exact=True).click()
        expect(pa.locator('.grant')).to_contain_text('5 releases remaining')
        pb.get_by_role('button',name='Refresh',exact=True).click()
        expect(pb.locator('.note-card')).to_have_count(1)
        pb.locator('#question').fill('What should I pack for the lakeside walk?')
        pb.get_by_role('button',name='Find an answer').click()
        pb.get_by_role('button',name='View once',exact=True).click(timeout=10000)
        expect(pb.locator('.answer-content')).to_contain_text('rain jacket')
        expect(pb.locator('.source-chip')).to_contain_text('Weekend at Pine Lake')
        pb.locator('#draft-text').fill('Check the weather before the walk.')
        pb.locator('#draft-form').get_by_role('button',name='Save',exact=True).click()
        expect(pb.locator('.draft-row')).to_contain_text('Check the weather')
        pb.get_by_role('button',name='Complete',exact=True).click()
        expect(pb.locator('.draft-row')).to_have_class('draft-row done')
        pb.evaluate('window.scrollTo(0,0)')
        pb.screenshot(path=str(ARTIFACTS/'workspace-desktop.png'),full_page=True)
        pb.get_by_role('button',name='Receipt history',exact=True).click()
        expect(pb.locator('#receipt-view')).to_contain_text('display reported')
        pb.screenshot(path=str(ARTIFACTS/'receipt-history.png'),full_page=True)
        pb.get_by_role('button',name='Close history',exact=True).click()
        pb.reload()
        expect(pb.locator('#job-list')).to_contain_text('Previously consumed; reload does not replay this answer.')
        expect(pb.locator('.answer-content')).to_have_count(0)
        expect(pb.locator('.draft-row')).to_contain_text('Check the weather')
        pa.get_by_role('button',name='Revoke',exact=True).click()
        pb.get_by_role('button',name='Refresh',exact=True).click()
        expect(pb.locator('.note-card')).to_have_count(0)
        expect(pb.locator('#job-list')).to_contain_text('source eligibility changed')
        pa.get_by_role('button',name='Edit',exact=True).first.click()
        pa.locator('#note-text').fill('The walk now starts at 10. Pack an umbrella.')
        pa.get_by_role('button',name='Save note',exact=True).click()
        expect(pa.locator('.note-card')).to_contain_text('revision 2')
        pa.set_viewport_size({'width':390,'height':844})
        pa.screenshot(path=str(ARTIFACTS/'workspace-mobile.png'),full_page=True)
        assert pa.locator('body').evaluate('(node) => node.scrollWidth <= window.innerWidth')
        result={'status':'PASS','url':owner['url'],'scenarios':['A/B demo login','private note isolation','explicit sharing','source-linked useful deterministic answer','first consumption','source card','four-record receipt UI','task persistence/completion','reload no payload replay','revoke hides source','revision edit','mobile no horizontal overflow'], 'console_errors':errors,'model_calls':0,'screenshots':['workspace-desktop.png','receipt-history.png','workspace-mobile.png']}
        assert errors==[],errors
        (ARTIFACTS/'browser-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    except Exception as error:
        for name,page in [('A',pa),('B',pb)]:
            page.screenshot(path=str(ARTIFACTS/('failure-'+name+'.png')),full_page=True)
        (ARTIFACTS/'browser-failure.json').write_text(json.dumps({'error':str(error),'console_errors':errors},indent=2)+'\n')
        raise
    finally:
        browser.close()
