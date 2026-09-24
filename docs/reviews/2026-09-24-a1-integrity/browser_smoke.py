"""Offline DOM smoke: no browser network, no auth-bootstrap/HTTP integration claim."""
from pathlib import Path
import argparse
import json
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from app import server as s, controller as c
from app.store import Store
from app.report import build_report
from playwright.sync_api import sync_playwright, expect

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output', type=Path, required=True, help='Local synthetic evidence directory; do not publish real data')
ap.add_argument('--chromium', help='Optional installed Chromium executable')
args = ap.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='dml-dom-') as tmp:
    store = Store(Path(tmp) / 'journal.db')
    ctl = c.Controller(store, c.MockExecutor(), max_parallel=0)
    def request(path, opts):
        body = json.loads(opts.get('body') or '{}')
        parts = path.strip('/').split('/')
        if path == '/api/options':
            data = {'participants': [vars(p) for p in s.PARTICIPANTS.values()], 'behaviors': list(s.BEHAVIORS)}
        elif path == '/api/state': data = ctl.view()
        elif path == '/api/runs':
            specs = [c.ParticipantSpec(**{**vars(s.PARTICIPANTS[item['pid']]), 'behavior': item['behavior']})
                     for item in body['participants']]
            data = {'run_id': ctl.create_run(body['question'], specs, min_independent=body['min_independent'],
                                            quorum_policy=body['quorum_policy'])}
        elif len(parts) == 5 and parts[3] == 'manual':
            ctl.submit_manual(parts[2], parts[4], body['text'], body['input_sha256'],
                              user_confirmed=body['user_confirmed'])
            data = {'ok': True}
        elif len(parts) == 4 and parts[3] == 'report': data = build_report(ctl.view(), parts[2])
        else: raise AssertionError(path)
        return data
    try:
        html = s.STATIC.joinpath('index.html').read_text()
        start = html.index('const TOKEN ='); end = html.index('window.addEventListener', start)
        # Only auth bootstrap and fetch transport are fixtures; the UI/report code remains unchanged.
        html = html[:start] + '''const TOKEN = "offline-fixture";
window.fetch = async (path, opts) => ({ok:true, json:async () => window.fixtureRequest(path, opts || {})});
''' + html[end:]
        errors = []
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.chromium, headless=True)
            page = browser.new_page(viewport={'width':1280, 'height':1000}, accept_downloads=True)
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.route('**/*', lambda route: route.abort())  # No HTTP/browser-network requests at all.
            page.expose_function('fixtureRequest', request)
            page.set_content(html)
            page.locator('#p-claude').uncheck(); page.locator('#p-codex').uncheck()
            page.locator('#question').fill('한글 보고 저장 검증: 공개된 초안을 그대로 보존하는가?')
            page.locator('#min').fill('1'); page.locator('#policy').select_option('include_unverified')
            page.locator('#start').click()
            expect(page.get_by_label('ChatGPT 앱 답')).to_be_visible()
            download = page.get_by_role('button', name='합성 없는 보고 저장(JSON · 원문 포함)', exact=True)
            expect(download).to_have_count(0)
            answer = '결론: 합성 없이 원문을 보존한다.\n반례: 출처와 미확인 상태가 빠지면 안 된다.\n<script>window.reportInjected = true</script>'
            page.get_by_label('ChatGPT 앱 답').fill(answer)
            page.get_by_role('button', name='답 넣기', exact=True).click()
            expect(download).to_be_visible()
            expect(page.locator('.draft')).to_have_text(answer)
            assert page.evaluate('window.reportInjected === undefined')
            with page.expect_download(timeout=5000) as event: download.click()
            event.value.save_as(out / 'report.json')
            report = json.loads((out / 'report.json').read_text())
            assert report['participants'][0]['draft'] == answer
            assert report['participants'][0]['independence'] == 'unverified'
            assert report['accounting']['attempts']['used'] == 0
            page.screenshot(path=str(out / 'desktop.png'), full_page=True)
            page.set_viewport_size({'width':390, 'height':844})
            page.screenshot(path=str(out / 'mobile.png'), full_page=True)
            dimensions = page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
            assert not errors, errors
            assert dimensions['scroll'] <= dimensions['width'], dimensions
            result = {'mode':'offline DOM/controller fixture; HTTP and auth bootstrap not exercised',
                      'chromium':browser.version, 'page_errors':errors, 'model_calls':0,
                      'download_preserved_original':True, 'script_rendered_as_text':True,
                      'pre_reveal_download_absent':True, 'mobile_dimensions':dimensions}
            (out / 'result.json').write_text(json.dumps(result, indent=2))
            print(json.dumps(result))
            browser.close()
    finally: store.close()
