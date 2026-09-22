"""Ledger 일반 글자 대비 감사. 보고 모드는 실패 쌍이 있어도 0; --strict는 1.

WCAG 2.2의 불투명 sRGB 대비 계산만 한다. 실제 DOM/CSS, 큰 글자 예외,
포커스·접근성 전체 준수나 글자 잘림을 검증하지 않는다.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

FOREGROUNDS = ("ink-000", "ink-100", "ink-200", "accent", "supported",
               "qualified", "rejected", "unresolved", "unknown", "sealed", "danger")
BACKGROUNDS = ("surface-000", "surface-100", "surface-200")


def luminance(color: str) -> float:
    if not isinstance(color, str) or re.fullmatch(r"#[0-9a-fA-F]{6}", color) is None:
        raise ValueError("opaque six-digit sRGB hex required")
    values = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
    return sum(v*w for v, w in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(foreground: str, background: str) -> float:
    low, high = sorted((luminance(foreground), luminance(background)))
    return (high + 0.05) / (low + 0.05)


def audit(document: dict) -> list[dict]:
    tokens = document["color"]["tokens"]
    palette = {t["name"]: t["value"] for t in tokens}
    if len(palette) != len(tokens):
        raise ValueError("duplicate color token")
    rows = []
    for theme in ("light", "dark"):
        for fg in FOREGROUNDS:
            for bg in BACKGROUNDS:
                ratio = contrast(palette[fg][theme], palette[bg][theme])
                rows.append({"theme": theme, "foreground": fg, "background": bg,
                             "ratio": round(ratio, 4), "passes_normal_text": ratio >= 4.5})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tokens", nargs="?", type=Path,
                        default=Path(__file__).resolve().parents[1] / "design/project/tokens.json")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        rows = audit(json.loads(args.tokens.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"INVALID: {exc}\n")
    failed = [r for r in rows if not r["passes_normal_text"]]
    print(json.dumps({"scope": "normal-text token pairs only; not rendered accessibility certification",
                      "pairs": len(rows), "failing_pairs": len(failed), "failures": failed}, ensure_ascii=False, indent=2))
    return 1 if args.strict and failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
