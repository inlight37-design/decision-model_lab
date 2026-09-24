"""오프라인 DOM 취소 시험. 브라우저 네트워크/인증 bootstrap/실제 CLI 시험이 아니다."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from app import controller as c, server as s
from app.store import Store
from playwright.sync_api import sync_playwright, expect


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chromium", default=None)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "journal.db")
        try:
            ctl = c.Controller(store, c.MockExecutor(), max_parallel=0)
            rid = ctl.create_run("취소 확인", [s.PARTICIPANTS["claude"], s.PARTICIPANTS["chatgpt-app"]], min_independent=1)
            def request(path, opts):
                if path == "/api/options":
                    return {"participants": [vars(p) for p in s.PARTICIPANTS.values()], "behaviors": list(s.BEHAVIORS)}
                if path == "/api/state":
                    return ctl.view()
                if path == f"/api/runs/{rid}/cancel":
                    ctl.cancel_run(rid)
                    return {"ok": True}
                raise AssertionError(path)
            html = (s.STATIC / "index.html").read_text(encoding="utf-8")
            start, end = html.index("const TOKEN ="), html.index("window.addEventListener")
            html = html[:start] + '''const TOKEN = "offline-fixture";
window.fetch = async (path, opts) => ({ok:true, json:async () => window.fixtureRequest(path, opts || {})});
''' + html[end:]
            errors = []
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=args.chromium, headless=True)
                try:
                    page = browser.new_page(viewport={"width": 390, "height": 950})
                    page.on("pageerror", lambda exc: errors.append(str(exc)))
                    page.on("dialog", lambda dialog: dialog.accept())
                    page.route("**/*", lambda route: route.abort())
                    page.expose_function("fixtureRequest", request)
                    page.set_content(html)
                    page.get_by_role("button", name="이 실행 취소", exact=True).click()
                    expect(page.get_by_role("button", name="이 실행 취소", exact=True)).to_have_count(0)
                    expect(page.get_by_text("시작 전 취소", exact=True)).to_have_count(2)
                    expect(page.locator("#detail textarea")).to_have_count(0)
                    expect(page.get_by_role("button", name="축소 승인", exact=True)).to_have_count(0)
                    expect(page.get_by_role("button", name="합성 없는 보고 저장", exact=False)).to_have_count(0)
                    assert ctl.view(rid)["runs"][0]["budget"]["used"] == 0
                    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                    assert not errors, errors
                    print(json.dumps({"offline_dom_cancel": "ok", "width": 390, "page_errors": errors,
                                      "network_test": False, "real_model_calls": 0}))
                finally:
                    browser.close()
        finally:
            store.close()


if __name__ == "__main__":
    main()
