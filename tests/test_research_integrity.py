"""Offline reference integrity; does not verify external sources or their truth."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

from tools.validate_v02 import strict_load

ROOT = Path(__file__).resolve().parents[1]

try:
    import jsonschema  # noqa: F401
    HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover - 환경에 따라 달라진다
    HAS_JSONSCHEMA = False

# version, prefix, source numbers, decision numbers, ADR file,
# 비어 있으면 안 되는 텍스트 필드, 날짜 필드 후보(하나 이상 필요)
REGISTRIES = (
    ("v0.3", "E", range(1, 32), range(1, 10), "04-decisions-and-evaluation.md",
     ("title", "kind", "locator", "claim", "limitations", "verification"),
     ("published",)),
    ("v0.4", "F", range(1, 30), range(10, 19), "02-frontier-architecture.md",
     ("title", "kind", "locator", "claim", "limits", "inspection"),
     ("published", "revised", "revision")),
)

# 현재 안내 문서. 과거 검토 기록(FINAL_REVIEW, VALIDATION 1-4절)은 그 시점의
# 숫자를 유지하는 것이 정확하므로 여기에 넣지 않는다.
CURRENT_GUIDANCE = (
    "docs/architecture/README.md",
    "docs/architecture/v0.4/README.md",
    "docs/architecture/v0.4/HANDOFF.md",
)

COMMIT_SHA = re.compile(r"\b[0-9a-f]{40}\b")


def evidence_ids(text):
    def expand(match):
        prefix, start, end = match.groups()
        return "/".join(f"{prefix}{i:02}" for i in range(int(start), int(end) + 1))
    text = re.sub(r"([EF])(\d{2})[–-](?:[EF])?(\d{2})", expand, text)
    return set(re.findall(r"\b[EF]\d{2}\b", text))


class ResearchIntegrityTests(unittest.TestCase):
    def test_registry_ids_and_decisions(self):
        for version, prefix, numbers, decisions, _, _, _ in REGISTRIES:
            with self.subTest(version=version):
                data = strict_load(ROOT / "docs/architecture" / version / "sources.json")
                sources = data["sources"]
                self.assertEqual(len(sources), len(numbers))
                self.assertEqual({s["id"] for s in sources}, {f"{prefix}{i:02}" for i in numbers})
                allowed = {f"D{i:02}" for i in decisions}
                for source in sources:
                    self.assertTrue(source["decisions"])
                    self.assertEqual(len(source["decisions"]), len(set(source["decisions"])))
                    self.assertTrue(set(source["decisions"]) <= allowed)
                    self.assertTrue(source["url"].startswith("https://"))

    def test_registry_entries_carry_their_epistemic_fields(self):
        """원장의 가치는 limits/inspection/locator 에 있다. 비어 있으면 기록이 아니다."""
        for version, _, _, _, _, text_fields, date_fields in REGISTRIES:
            data = strict_load(ROOT / "docs/architecture" / version / "sources.json")
            for source in data["sources"]:
                for field in text_fields:
                    with self.subTest(version=version, id=source["id"], field=field):
                        self.assertTrue(
                            str(source.get(field, "")).strip(),
                            f"{source['id']}: '{field}' is missing or blank",
                        )
                # 가변 문서일수록 날짜가 중요하다. 모르면 published: null 로 명시하고
                # 필드를 생략하지 않는다. 생략과 '모른다'는 서로 다른 상태다.
                with self.subTest(version=version, id=source["id"], field="date"):
                    self.assertTrue(
                        any(field in source for field in date_fields),
                        f"{source['id']}: needs one of {date_fields}; use null when unknown",
                    )

    def test_adr_and_registry_mappings_are_bidirectional(self):
        for version, _, _, decisions, filename, _, _ in REGISTRIES:
            folder = ROOT / "docs/architecture" / version
            expected = {f"D{i:02}": set() for i in decisions}
            for source in strict_load(folder / "sources.json")["sources"]:
                for decision in source["decisions"]:
                    expected[decision].add(source["id"])
            actual = {}
            for line in (folder / filename).read_text(encoding="utf-8").splitlines():
                match = re.match(r"\| (D\d{2}) \|", line)
                if match:
                    self.assertNotIn(match[1], actual)
                    actual[match[1]] = evidence_ids(line)
            with self.subTest(version=version):
                self.assertEqual(actual, expected)

    def test_current_guidance_states_the_actual_registry_range(self):
        """원장이 커지면 안내 문서의 범위 표기도 따라와야 한다. F22-F24 추가 때 놓쳤던 회귀."""
        for version, prefix, numbers, _, _, _, _ in REGISTRIES:
            expected = f"{prefix}01–{prefix}{max(numbers):02}"
            stale = re.compile(rf"{prefix}01–(?:{prefix})?\d{{2}}")
            for relative in CURRENT_GUIDANCE:
                for number, line in enumerate((ROOT / relative).read_text(encoding="utf-8").splitlines(), 1):
                    # commit SHA 가 있는 줄은 그 시점의 이력이므로 당시 범위가 정확하다.
                    if COMMIT_SHA.search(line):
                        continue
                    for found in stale.finditer(line):
                        with self.subTest(doc=relative, line=number, found=found.group(0)):
                            self.assertEqual(
                                found.group(0), expected,
                                f"{relative}:{number}: stale registry range; "
                                f"registry holds {len(numbers)} entries",
                            )

    @unittest.skipUnless(HAS_JSONSCHEMA,
                         "jsonschema 미설치: python -m pip install -r requirements-design.txt")
    def test_registries_match_the_published_contract(self):
        from tools.validate_sources import REGISTRIES as CONTRACTS, errors_for

        schema = strict_load(ROOT / "contracts/sources.schema.json")
        for relative, definition in CONTRACTS:
            with self.subTest(registry=relative):
                registry = strict_load(ROOT / relative)
                self.assertEqual(errors_for(registry, definition, schema), [])

    def test_text_files_are_utf8_without_a_bom(self):
        """pre-commit hook 과 같은 검사를 한 번 더 돈다. hook 은 --no-verify 로 우회할 수
        있으므로 CI 에서도 확인한다. 구현은 tools/check_encoding.py 하나뿐이다."""
        from tools.check_encoding import problems, tracked_files

        paths = tracked_files()
        self.assertTrue(paths, "검사 대상 파일을 하나도 찾지 못했다")
        self.assertEqual(problems(paths), [])

    def test_markdown_relative_link_targets_exist(self):
        # Inline Markdown file links only; external URLs and heading anchors are not checked.
        paths = list(ROOT.glob("*.md"))
        for folder in ("docs", "contracts"):
            paths.extend((ROOT / folder).rglob("*.md"))
        for path in paths:
            # 보관한 인계 문서는 루트에서 쓴 원문을 바이트 그대로 둔다(docs/handoff/README.md).
            if path.parent == ROOT / "docs/handoff" and path.name != "README.md":
                continue
            content = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
            for target in re.findall(r"\[[^\]\n]*\]\(([^)\s]+)\)", content):
                parts = urlsplit(target)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                with self.subTest(path=path.relative_to(ROOT), target=target):
                    self.assertTrue((path.parent / unquote(parts.path)).exists())


if __name__ == "__main__":
    unittest.main()
