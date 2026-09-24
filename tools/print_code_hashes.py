#!/usr/bin/env python3
"""현재 검사 코드의 Git blob SHA-1을 출력한다. 표준 라이브러리만 사용한다.

문서에 hash를 고정하면 코드가 바뀌는 순간 낡는다. 대신 이 도구를 실행해
검토 시점의 값을 기록한다. Git blob 해시는 `blob <byte_length>\\0<content>`
에 대한 SHA-1이며 일반 파일 SHA-1과 다르다.

실행: python tools/print_code_hashes.py [--json]
이 도구는 원격과의 일치를 증명하지 않는다. 출력값을 GitHub의 blob SHA와
직접 대조해야 동일성 확인이 된다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 검증 기록에서 동일성을 주장하는 대상. 새 검사 코드를 추가하면 여기에도 넣는다.
TRACKED = (
    "tools/check_frontier_protocol.py",
    "tools/validate_v02.py",
    "tools/validate_design.py",
    "tools/validate_sources.py",
    "tools/validate_design_tokens.py",
    "tools/check_encoding.py",
    "tools/review_boundary.py",
    "tools/audit_design_contrast.py",
    "tools/runtime_inventory.py",
    "tests/test_frontier_protocol.py",
    "tests/test_research_integrity.py",
    "tests/test_v02.py",
    "tests/test_review_boundary.py",
    "tests/test_design_contrast.py",
    "tests/test_runtime_inventory.py",
)


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def collect() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for rel in TRACKED:
        path = ROOT / rel
        if not path.is_file():
            rows.append({"path": rel, "error": "missing"})
            continue
        data = path.read_bytes()
        rows.append({"path": rel, "bytes": len(data), "blob_sha1": git_blob_sha1(data)})
    return rows


def main() -> int:
    # Windows의 리디렉션된 출력은 CP1252일 수도 있다. 한글 결과 줄이 검사를 실패시키지 않게 UTF-8로 고정한다.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Print Git blob SHA-1 of the checker code.")
    parser.add_argument("--json", action="store_true", help="기계 판독용 JSON 출력")
    args = parser.parse_args()

    rows = collect()
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        width = max(len(str(r["path"])) for r in rows)
        for row in rows:
            if "error" in row:
                print(f"{str(row['path']):<{width}}  MISSING")
            else:
                print(f"{str(row['path']):<{width}}  bytes={row['bytes']:<6} blob={row['blob_sha1']}")
        print("\n이 값은 로컬 파일의 해시다. 원격 동일성은 GitHub blob SHA와 대조해야 확인된다.")
    return 1 if any("error" in r for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
