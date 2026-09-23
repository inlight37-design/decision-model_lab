"""화면(app/static/index.html)의 글자 대비 검사(인계 N6, K24). 브라우저 렌더링이 아니라 CSS의 색 조합만 본다.

화면은 디자인 토큰 값을 :root에 복사해 쓴다. 그 복사본이 design/project/tokens.json과 같은지, 상태 라벨과 작은
글자가 쓰는 색이 그 배경 위에서 두 테마 모두 일반 글자 기준(4.5:1)을 넘는지 확인한다.
"""
import json
from pathlib import Path
import re
import unittest

from tools.audit_design_contrast import contrast

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
CSS = HTML[HTML.index("<style>"):HTML.index("</style>")]
TOKEN = re.compile(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})")


def themes() -> dict[str, dict[str, str]]:
    dark_at = CSS.index("@media (prefers-color-scheme: dark)")
    return {"light": dict(TOKEN.findall(CSS[:dark_at])), "dark": dict(TOKEN.findall(CSS[dark_at:CSS.index("}", CSS.index("{", dark_at) + 1)]))}


def rule(selector: str) -> str:
    found = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    if found is None:
        raise AssertionError(f"no CSS rule for {selector}")
    return found.group(1)


def color_of(body: str) -> str:
    return re.search(r"(?<![-\w])color:\s*var\(--([a-z0-9-]+)\)", body).group(1)


class ScreenContrastTests(unittest.TestCase):
    def test_the_screen_copies_the_design_tokens_unchanged(self):
        design = {t["name"]: t["value"] for t in
                  json.loads((ROOT / "design/project/tokens.json").read_text(encoding="utf-8"))["color"]["tokens"]}
        for theme, tokens in themes().items():
            for name, value in tokens.items():
                if name in design:
                    with self.subTest(theme=theme, token=name):
                        self.assertEqual(value.lower(), design[name][theme].lower())

    def test_state_labels_and_small_text_meet_normal_text_contrast(self):
        uses = [(color_of(body), "surface-100", selector)
                for selector, body in re.findall(r"(\.st-[a-z_]+(?:,\s*\.st-[a-z_]+)*)\s*\{([^}]*)\}", CSS)]
        uses += [(color_of(rule(".revealed .st-accepted")), "surface-100", ".revealed .st-accepted"),
                 (color_of(rule(".who .v")), "surface-100", ".who .v"),
                 (color_of(rule(".trail")), "surface-000", ".trail"),
                 (color_of(rule(".meta")), "surface-100", ".meta"),
                 (color_of(rule(".caption")), "surface-000", ".caption"),
                 (color_of(rule(".kv")), "surface-100", ".kv"),
                 (color_of(rule(".flag")), "surface-100", ".flag"),
                 (color_of(rule(".foot .warn")), "surface-100", ".foot .warn")]
        self.assertGreaterEqual(len(uses), 12)
        for theme, tokens in themes().items():
            for fg, bg, selector in uses:
                with self.subTest(theme=theme, selector=selector, colors=(fg, bg)):
                    self.assertGreaterEqual(contrast(tokens[fg], tokens[bg]), 4.5)

    def test_unknown_keeps_its_dashed_mark_without_colouring_the_text(self):
        """K24. unknown 색은 글자 대비가 모자라 글자에는 쓰지 않는다. 관측하지 못했다는 표시는 1px 파선으로 남긴다."""
        body = rule(".st-unknown")
        self.assertNotEqual(color_of(body), "unknown")
        self.assertRegex(body, r"border-bottom:\s*1px dashed var\(--unknown\)")
        for theme, tokens in themes().items():
            with self.subTest(theme=theme):
                self.assertGreaterEqual(contrast(tokens["unknown"], tokens["surface-100"]), 3.0)  # 글자가 아닌 표시


if __name__ == "__main__":
    unittest.main()
