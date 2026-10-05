"""LAN-account Chromium smoke test at iPhone-sized viewport.

No model inference and no external network requests. Requires developer-provided
Playwright + Chromium, matching browser_smoke.py.
"""
from pathlib import Path
import os
import shutil
import sys
import tempfile
import threading
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from labcore import Lab
from server import Server
from playwright.sync_api import sync_playwright, expect


with tempfile.TemporaryDirectory(prefix='haven-lan-browser-') as t:
    lab = Lab(Path(t))
    server = Server(('127.0.0.1', 0), lab, lan_mode=True, control_token='browser-test-control')
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    errors, external = [], []
    try:
        with sync_playwright() as p:
            chromium = (
                os.environ.get('HAVEN_TEST_CHROMIUM')
                or shutil.which('chromium')
                or shutil.which('chromium-browser')
                or (p.chromium.executable_path if Path(p.chromium.executable_path).is_file() else None)
            )
            if not chromium:
                raise SystemExit('Provide HAVEN_TEST_CHROMIUM; no automatic browser download.')
            browser = p.chromium.launch(executable_path=chromium, headless=True, chromium_sandbox=True)
            try:
                owner = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=3)
                page = owner.new_page()
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('request', lambda r: external.append(r.url) if urlsplit(r.url).hostname not in ('127.0.0.1', None) else None)
                page.goto(f'http://127.0.0.1:{server.server_port}/#bootstrap={server.bootstrap_token}')
                expect(page.locator('#auth-bootstrap')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1')
                page.locator('#bootstrap-username').fill('owner')
                page.locator('#bootstrap-password').fill('correct horse battery staple')
                page.locator('#bootstrap-confirm').fill('correct horse battery staple')
                page.locator('#bootstrap-form button[type=submit]').click()
                expect(page.locator('#account-button')).to_contain_text('owner')
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1')

                page.locator('#account-button').click()
                expect(page.locator('#account-dialog')).to_be_visible()
                page.locator('#create-invite').click()
                expect(page.locator('#invite-link')).not_to_have_value('')
                invite_url = page.locator('#invite-link').input_value()
                page.locator('#account-close').click()

                member = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=3)
                phone = member.new_page()
                phone.on('pageerror', lambda e: errors.append(str(e)))
                phone.on('request', lambda r: external.append(r.url) if urlsplit(r.url).hostname not in ('127.0.0.1', None) else None)
                phone.goto(invite_url)
                expect(phone.locator('#auth-invite')).to_be_visible()
                phone.locator('#invite-username').fill('iphone')
                phone.locator('#invite-password').fill('another correct horse battery')
                phone.locator('#invite-confirm').fill('another correct horse battery')
                phone.locator('#invite-form button[type=submit]').click()
                expect(phone.locator('#account-button')).to_contain_text('iphone')
                expect(phone.locator('[data-view="setup"]')).to_have_class('nav admin-only hidden')
                expect(phone.locator('#prompt')).to_be_visible()
                assert phone.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1')
                phone.screenshot(path=str(Path(t) / 'iphone-member.png'), full_page=True)
                member.close()
                owner.close()
            finally:
                browser.close()
        assert not errors, errors
        assert not external, external
        print('PASS: 390x844 owner setup, invite redemption, member permissions, and no horizontal overflow.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)
        lab.shutdown()
