#!/usr/bin/env python3
r"""추적 대상 텍스트 파일이 BOM 없는 UTF-8 인지 검사한다. 표준 라이브러리만 사용한다.

왜 필요한가
-----------
Windows PowerShell 5.1 의 `Get-Content` 는 BOM 이 없는 UTF-8 파일을 시스템 ANSI
코드페이지(한국어 Windows 에서는 CP949)로 읽는다. 그 결과를 `Set-Content -Encoding utf8`
로 되쓰면 BOM 이 붙고, CP949 로 표현할 수 없던 글자는 `?` 로 사라진다. 한국어 저장소에서는
문서 한 번 일괄 치환하는 것만으로 본문이 망가진다.

이 검사가 잡는 것: UTF-8 BOM, UTF-8 로 디코딩되지 않는 바이트, 탭·줄바꿈 외의 제어 문자.
제어 문자는 스크립트로 문서를 고칠 때 생긴다. 파이썬 일반 문자열에 Windows 경로
`\.local\bin` 을 넣으면 `\b` 가 백스페이스(0x08)가 되어 화면에서 글자가 사라진다(실제로 있었다).
이 검사가 **잡지 못하는 것**: CP949 로 잘못 읽혀 생긴 '그럴듯한 다른 한글'. 그것은 유효한
UTF-8 이므로 사람이 읽어야 발견된다. 그래서 이 검사는 마지막 방어선이 아니라 첫 번째 방어선이다.

실행:
    python tools/check_encoding.py              # 저장소 전체
    python tools/check_encoding.py a.md b.json  # 지정한 파일만 (pre-commit hook 용)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 본문이 한글을 담을 수 있는 텍스트 파일. 바이너리와 생성물은 대상이 아니다.
SUFFIXES = (".md", ".json", ".py", ".yml", ".yaml", ".toml", ".txt", ".html", ".css", ".js", ".ps1")
SKIP_PARTS = ("__pycache__", ".git", ".venv", "venv", "node_modules")

BOM = b"\xef\xbb\xbf"
# 탭(0x09)·줄바꿈(0x0A)·CR(0x0D)만 허용한다. 나머지 C0 제어 문자와 DEL 은 편집 사고다.
CONTROL = {c for c in range(0x20) if c not in (0x09, 0x0A, 0x0D)} | {0x7F}


def tracked_files() -> list[Path]:
    found: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        found.append(path)
    return sorted(found)


def problems(paths: list[Path]) -> list[str]:
    """각 파일의 문제를 사람이 읽을 수 있는 한 줄로 돌려준다. 빈 목록이면 통과."""
    found: list[str] = []
    for path in paths:
        try:
            raw = path.read_bytes()
        except OSError as error:
            found.append(f"{path}: 읽을 수 없음 ({error})")
            continue
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError:
            relative = str(path)
        if raw.startswith(BOM):
            found.append(f"{relative}: UTF-8 BOM. PowerShell 의 Set-Content -Encoding utf8 왕복을 의심한다")
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as error:
            found.append(f"{relative}: UTF-8 로 디코딩되지 않음 (byte {error.start})")
        # UTF-8 에서 0x00-0x7F 바이트는 항상 그 ASCII 글자 자체이므로 바이트로 세도 된다.
        control = next((i for i, byte in enumerate(raw) if byte in CONTROL), None)
        if control is not None:
            line = raw.count(b"\n", 0, control) + 1
            found.append(f"{relative}:{line}: 제어 문자 0x{raw[control]:02x}. "
                         r"스크립트의 문자열 escape(\b, \f 등)를 의심한다")
    return found


def main() -> int:
    if len(sys.argv) > 1:
        paths = [Path(argument).resolve() for argument in sys.argv[1:]]
        paths = [path for path in paths if path.is_file() and path.suffix.lower() in SUFFIXES]
    else:
        paths = tracked_files()

    found = problems(paths)
    if found:
        print("인코딩 문제:")
        for message in found:
            print(f"  {message}")
        print("\n고치는 법: git checkout -- <path> 로 되돌리거나,")
        print("PowerShell 대신 편집 도구를 쓰거나, .NET 으로 인코딩을 명시한다:")
        print("  [IO.File]::WriteAllText($p, $text, [Text.UTF8Encoding]::new($false))")
        return 1

    print(f"PASS: {len(paths)}개 파일이 BOM 없는 UTF-8, 제어 문자 없음. "
          "CP949 오독으로 생긴 그럴듯한 한글은 이 검사로 잡히지 않는다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
