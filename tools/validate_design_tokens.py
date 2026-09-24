#!/usr/bin/env python3
"""디자인 시스템 토큰의 문법을 검사한다. 표준 라이브러리만 사용한다.

왜 필요한가
-----------
발행 페이지는 문법에 맞지 않는 값을 **조용히 버린다.** hex 오타 하나면 그 색이
통째로 사라지고, 화면에서는 그냥 상속된 색으로 보여 알아채기 어렵다. 실제로
`#f徒` 와 `#d6a košice` 로 두 번 겪었다. 행간이 글자보다 좁으면 g·y 의 디센더가
잘리는데 이것도 눈으로만 찾으면 놓친다.

검사하는 것: 이름 규칙, 중복(드롭 원인), hex 형식, 길이 형식, usage 존재,
lineHeight >= fontSize * 1.25.
검사하지 않는 것: 대비비, 색의 적절성, 컴포넌트 미리보기의 정확성.

실행: python tools/validate_design_tokens.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "design/project/tokens.json"

HEX = re.compile(r"^#(?:[0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})$")
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
LENGTH = re.compile(r"^(?:-?\d+(?:\.\d+)?(?:px|rem|em|%)?|0)$")
MIN_LINE_RATIO = 1.25


def number(value: str) -> float:
    return float(re.sub(r"[a-z%]+$", "", str(value)) or 0)


def problems(data: dict) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    themes = [t["id"] for t in data["color"]["themes"]]
    for token in data["color"]["tokens"]:
        name = token["name"]
        if not NAME.match(name):
            found.append(f"color {name}: 이름 규칙 위반")
        if name in seen:
            found.append(f"color {name}: 중복 → 드롭")
        seen.add(name)
        raw = token["value"]
        values = raw if isinstance(raw, dict) else {themes[0]: raw}
        for theme, value in values.items():
            text = str(value)
            if not (HEX.match(text) or (text.startswith("{") and text.endswith("}"))):
                found.append(f"color {name}[{theme}] = {value!r}: hex/alias 아님 → 드롭")
        if not str(token.get("usage", "")).strip():
            found.append(f"color {name}: usage 없음")

    for family in ("spacing", "radius", "shadow"):
        for token in data.get(family, {}).get("tokens", []):
            name = token["name"]
            if name in seen:
                found.append(f"{family} {name}: 중복 → 드롭")
            seen.add(name)
            if family in ("spacing", "radius") and not LENGTH.match(str(token["value"])):
                found.append(f"{family} {name} = {token['value']!r}: 길이 아님 → 드롭")

    styles: set[str] = set()
    for group in data["type"]["groups"]:
        if group["family"] not in data["type"]["families"]:
            found.append(f"group {group['name']}: families 에 {group['family']} 없음")
        for style in group["styles"]:
            name = style["name"]
            if name in styles:
                found.append(f"style {name}: 중복")
            styles.add(name)
            if not LENGTH.match(str(style["fontSize"])):
                found.append(f"style {name}: fontSize 불량 → 스타일 드롭")
                continue
            line = str(style["lineHeight"])
            if line.endswith("px"):
                size, height = number(style["fontSize"]), number(line)
                if height < size * MIN_LINE_RATIO:
                    found.append(
                        f"style {name}: lineHeight {line} < fontSize {size}px × {MIN_LINE_RATIO}"
                        " → 디센더 잘림"
                    )
    return found


def main() -> int:
    # Windows의 리디렉션된 출력은 CP1252일 수도 있다. 한글 결과 줄이 검사를 실패시키지 않게 UTF-8로 고정한다.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not TOKENS.is_file():
        print(f"없음: {TOKENS.relative_to(ROOT)}")
        return 1

    data = json.loads(TOKENS.read_text(encoding="utf-8"))
    found = problems(data)
    counts = (
        f"color {len(data['color']['tokens'])} · "
        f"spacing {len(data['spacing']['tokens'])} · "
        f"radius {len(data['radius']['tokens'])} · "
        f"styles {sum(len(g['styles']) for g in data['type']['groups'])}"
    )
    if found:
        print(f"FAIL {TOKENS.relative_to(ROOT)} ({counts})")
        for message in found:
            print(f"     {message}")
        return 1

    print(f"PASS {TOKENS.relative_to(ROOT)} ({counts})")
    print("범위: 토큰 문법과 행간만. 대비비와 색의 적절성은 사람이 본다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
