"""화면(app/static/index.html)의 글자 대비(인계 N6, K24). 브라우저 렌더링이 아니라 색 값만 계산한다.

화면은 island-ui 토큰(app/static/island-ui/themes.css)만 쓴다. 테마 세 벌에서 화면이 쓰는 글자·바탕 짝을 APCA
(SAPC 0.0.98G-4g 상수)로 재어 island-ui의 기준 Lc 60(36px 큰 숫자는 45)을 넘는지 본다. 반투명 바탕은 그 테마의
--bg 위에 겹친 색으로 본다 — 유리 테마의 바탕 번짐은 계산에 넣지 않는다. 판정 색(--unresolved 등)과 --text-3은
작은 글자에서 대비가 모자라 글자색으로 쓰지 않는다(ai_unslop exp-010에서 판정 색 13px 글자가 Lc 41~44였다).
"""
import math
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
THEMES_CSS = (ROOT / "app/static/island-ui/themes.css").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
PAGE_CSS = HTML[HTML.index("<style>"):HTML.index("</style>")]

# (글자, 아래에서 위로 겹친 바탕들). 바탕 목록의 맨 아래에는 늘 그 테마의 --bg가 깔린다.
PAIRS = [
    ("text", ("surface",)), ("text", ("surface", "surface-2")), ("text", ("surface", "surface-3")),
    ("text", ("surface", "primary-soft")),
    ("text-2", ("surface",)), ("text-2", ("surface", "surface-2")), ("text-2", ("surface", "surface-3")),
    ("on-primary", ("surface", "primary")), ("on-brand", ("surface", "brand")),
    ("on-tint-blue", ("surface", "tint-blue")), ("on-tint-orange", ("surface", "tint-orange")),
    ("on-tint-violet", ("surface", "tint-violet")),
    ("on-tint-orange", ("surface", "surface-2")),          # 파일 칸의 거절 안내
    ("on-hero", ("hero-1",)), ("on-hero", ("hero-2",)), ("on-hero-2", ("hero-1",)), ("on-hero-2", ("hero-2",)),
    ("on-hero", ("hero-2", "hero-chip-bg")),               # 결정 카드 안의 목록 칸
]
LARGE = [("hero-count", ("hero-1",)), ("hero-count", ("hero-2",))]   # 결정 카드의 36px 숫자
NOT_TEXT = ("text-3", "unresolved", "failed", "supported", "qualified", "rejected", "waiting")


def themes() -> dict[str, dict[str, str]]:
    found = {}
    for selector, body in re.findall(r"([^{}]+)\{([^}]*)\}", THEMES_CSS):
        name = re.search(r'data-theme="(\w+)"', selector)
        if name and "--bg:" in body:
            found[name.group(1)] = dict(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", body))
    return {name: {**found["light"], **tokens} for name, tokens in found.items()}


def oklch(lightness: float, chroma: float, hue: float) -> tuple[float, ...]:
    a, b = chroma * math.cos(math.radians(hue)), chroma * math.sin(math.radians(hue))
    l_, m_, s_ = (lightness + 0.3963377774 * a + 0.2158037573 * b, lightness - 0.1055613458 * a - 0.0638541728 * b,
                  lightness - 0.0894841775 * a - 1.2914855480 * b)
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    linear = (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
              -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
              -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)
    encode = lambda x: 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
    return tuple(min(1.0, max(0.0, encode(max(0.0, x)))) for x in linear)


def parse(value: str) -> tuple[tuple[float, ...], float]:
    """sRGB 0..1과 불투명도. 화면 토큰이 쓰는 세 표기(#hex, oklch(), rgba())만 읽는다."""
    value = value.strip()
    if value.startswith("#"):
        digits = value[1:]
        return tuple(int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4)), (int(digits[6:8], 16) / 255 if len(digits) == 8 else 1.0)
    if found := re.fullmatch(r"oklch\(([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*/\s*([\d.]+))?\)", value):
        return oklch(*map(float, found.groups()[:3])), float(found.group(4) or 1)
    if found := re.fullmatch(r"rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)", value):
        return tuple(float(x) / 255 for x in found.groups()[:3]), float(found.group(4) or 1)
    raise ValueError(f"unsupported colour {value!r}")


def over(top: tuple[tuple[float, ...], float], base: tuple[float, ...]) -> tuple[float, ...]:
    color, alpha = top
    return tuple(alpha * x + (1 - alpha) * y for x, y in zip(color, base))


def layered(tokens: dict[str, str], names: tuple[str, ...]) -> tuple[float, ...]:
    color = parse(tokens["bg"])[0]
    for name in names:
        color = over(parse(tokens[name]), color)
    return color


def apca(text: tuple[float, ...], background: tuple[float, ...]) -> float:
    luminance = lambda c: 0.2126729 * c[0] ** 2.4 + 0.7151522 * c[1] ** 2.4 + 0.0721750 * c[2] ** 2.4
    clamp = lambda y: y if y > 0.022 else y + (0.022 - y) ** 1.414
    t, b = clamp(luminance(text)), clamp(luminance(background))
    if b > t:
        s = (b ** 0.56 - t ** 0.57) * 1.14
        return 0.0 if s < 0.1 else (s - 0.027) * 100
    s = (b ** 0.65 - t ** 0.62) * 1.14
    return 0.0 if s > -0.1 else -(s + 0.027) * 100


class ScreenContrastTests(unittest.TestCase):
    def test_all_three_themes_are_read(self):
        self.assertEqual(set(themes()), {"light", "glass", "dusk"})

    def test_text_pairs_the_screen_uses_reach_the_island_ui_threshold(self):
        for theme, tokens in themes().items():
            for pairs, minimum in ((PAIRS, 60), (LARGE, 45)):
                for fg, bg in pairs:
                    background = layered(tokens, bg)
                    with self.subTest(theme=theme, text=fg, background=bg):
                        self.assertGreaterEqual(apca(over(parse(tokens[fg]), background), background), minimum)

    def test_verdict_colours_and_faint_grey_are_not_used_for_text(self):
        used = set(re.findall(r"(?<![-\w])color:\s*var\(--([a-z0-9-]+)\)", PAGE_CSS))
        self.assertTrue(used)
        self.assertFalse(used & set(NOT_TEXT), used & set(NOT_TEXT))

    def test_unknown_keeps_a_dashed_mark_without_colouring_the_text(self):
        """K24. 관측하지 못한 값은 글자를 흐리게 칠하지 않고 파선 밑줄로 표시한다 — 모르는 것은 0이 아니다."""
        body = re.search(r"\.st-unknown\s*\{([^}]*)\}", PAGE_CSS).group(1)
        self.assertRegex(body, r"text-decoration:\s*underline dashed")
        self.assertNotRegex(body, r"(?<![-\w])color:")


if __name__ == "__main__":
    unittest.main()
