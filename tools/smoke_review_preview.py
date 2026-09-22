"""별도 opt-in 브라우저 smoke. pip install playwright + Chromium 설치 필요.
전체 접근성/보안 인증이나 사용자 실험이 아니다. 외부 네트워크는 차단한다.
"""
from pathlib import Path
import argparse
import json
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', default=None, help='Chromium executable path')
    args = parser.parse_args()
    preview = Path(__file__).resolve().parents[1] / 'docs/reviews/2026-09-23-mcp-ui-runtime/preview.html'
    errors, external, cases = [], [], 0
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, headless=True)
        page = browser.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        def block(route):
            if route.request.url.startswith(('http://', 'https://')):
                external.append(route.request.url)
                route.abort()
            else:
                route.continue_()
        page.route('**/*', block)
        page.set_content(preview.read_text(encoding="utf-8"))
        for width in (320, 390, 1280):
            page.set_viewport_size({'width': width, 'height': 960})
            for mode in ('review', 'sealed', 'lost', 'empty'):
                page.select_option('#scenario', mode)
                for layout in ('decision-first', 'ledger-first'):
                    page.click('#'+layout)
                    for theme in ('light', 'dark'):
                        page.evaluate('(theme) => document.documentElement.dataset.theme = theme', theme)
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, mode, layout, theme)
                        assert '실제 provider 연결 0건' in page.inner_text('.notice')
                        cases += 1
        page.set_viewport_size({'width':1280, 'height':960})
        page.select_option('#scenario', 'review')
        page.click('#decision-first')
        assert page.locator('#main > section').first.get_attribute('id') == 'decision-panel'
        page.click('#ledger-first')
        assert page.locator('#main > section').first.get_attribute('id') == 'ledger-panel'
        page.locator('summary').focus()
        page.keyboard.press('Enter')
        assert page.locator('details').get_attribute('open') is not None
        page.locator('#theme').focus()
        page.keyboard.press('Space')
        assert page.locator('#theme').get_attribute('aria-pressed') == 'false'
        page.select_option('#scenario', 'lost')
        assert page.locator('#main').inner_text().count('UNKNOWN') == 1
        assert not page.locator('#main button').count()
        browser.close()
    assert not errors, errors
    assert not external, external
    print(json.dumps({'layout_cases':cases, 'page_errors':len(errors), 'external_requests':len(external),
                      'scope':'smoke only; no live provider, user study, or full accessibility audit'}))


if __name__ == '__main__':
    main()
