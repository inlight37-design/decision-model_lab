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

# 계속 갱신되는 안내 문서. 여러 세션과 여러 AI가 번갈아 고치므로 숫자가 가장 쉽게
# 어긋난다(75/74/71 검사, F01–F24 범위가 동시에 남아 있던 적이 있다).
# 과거 검토 기록(FINAL_REVIEW, VALIDATION 1-4절, docs/reviews/, 보관한 인계)은
# 그 시점의 숫자를 유지하는 것이 정확하므로 넣지 않는다. docs/COLLABORATION.md 참조.
LIVING_DOCS = (
    "README.md",
    "AGENTS.md",
    "NEXT-SESSION.md",
    "docs/COLLABORATION.md",
    "docs/architecture/README.md",
    "docs/architecture/v0.4/README.md",
    "docs/architecture/v0.4/HANDOFF.md",
    "docs/reviews/README.md",
    "docs/handoff/README.md",
    "design/README.md",
)

COMMIT_SHA = re.compile(r"\b[0-9a-f]{40}\b")

# 안내 문서가 다시 적으면 안 되는 개수. 기준은 CI 로그 하나다.
RESTATED_COUNT = re.compile(
    r"\b\d+\s*tests?\b"
    r"|(?:검사|테스트)[은는이가도를]?\s*\*{0,2}\d+\s*개"
    r"|\*{0,2}\d+\s*개\*{0,2}\s*(?:의\s*)?(?:검사|테스트)"
    r"|전체[은는]?\s*\*{0,2}\d+\s*개"
    r"|원장[은는이가]?\s*\*{0,2}\d+\s*(?:건|개)"
    r"|commit\s*\*{0,2}\d+\b",
    re.IGNORECASE,
)


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

    def living_lines(self):
        """안내 문서의 줄. commit SHA 가 있는 줄은 그 시점의 이력이므로 건너뛴다."""
        for relative in LIVING_DOCS:
            for number, line in enumerate((ROOT / relative).read_text(encoding="utf-8").splitlines(), 1):
                if not COMMIT_SHA.search(line):
                    yield relative, number, line

    def test_current_guidance_states_the_actual_registry_range(self):
        """원장이 커지면 안내 문서의 범위 표기도 따라와야 한다. F22-F24 추가 때 놓쳤던 회귀."""
        for version, prefix, numbers, _, _, _, _ in REGISTRIES:
            # en dash 와 hyphen 을 모두 잡는다. AGENTS.md 의 'F01-F24' 는 hyphen 이라 빠져 있었다.
            stale = re.compile(rf"{prefix}01[–-](?:{prefix})?(\d{{2}})")
            for relative, number, line in self.living_lines():
                for found in stale.finditer(line):
                    with self.subTest(doc=relative, line=number, found=found.group(0)):
                        self.assertEqual(
                            int(found.group(1)), max(numbers),
                            f"{relative}:{number}: stale registry range; "
                            f"registry holds {prefix}01–{prefix}{max(numbers):02}",
                        )

    def test_living_documents_do_not_restate_counts(self):
        """검사 수·원장 건수·commit 수는 CI 로그와 원장이 기준이다. 안내 문서에 다시 적으면
        다음 세션이 고치지 않는 한 틀린 채로 남는다. 그 시점의 숫자가 필요하면 commit SHA 와
        같은 줄에 적는다 — 그 줄은 이력으로 취급한다."""
        for relative, number, line in self.living_lines():
            for found in RESTATED_COUNT.finditer(line):
                with self.subTest(doc=relative, line=number, found=found.group(0)):
                    self.fail(f"{relative}:{number}: '{found.group(0)}' — link the CI log instead")

    def test_handoff_keeps_its_fixed_layout(self):
        """여러 세션이 번갈아 쓰는 인계 문서는 같은 자리에서 같은 것을 찾을 수 있어야 한다.
        '진행 중인 작업' 절이 없으면 main 의 인계가 열린 PR 을 모르는 일이 되풀이된다."""
        lines = (ROOT / "NEXT-SESSION.md").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "# 다음 세션 인계 — decision-model_lab")
        self.assertTrue(
            any(re.match(r"최종 갱신 \*\*\d{4}-\d{2}-\d{2}\*\* · 작성 세션: \S", line) for line in lines[:5]),
            "second block must read '최종 갱신 **YYYY-MM-DD** · 작성 세션: <agent>'",
        )
        self.assertEqual(
            [line for line in lines if line.startswith("## ")],
            ["## 0. 먼저 확인할 것", "## 1. 지금 상태", "## 2. 사용자가 확정한 것",
             "## 3. 진행 중인 작업", "## 4. 다음 작업", "## 5. 하지 말 것", "## 6. 검사"],
        )

    def test_restated_count_pattern_matches_past_drift(self):
        """위 검사가 실제로 있었던 어긋남을 잡는지, 정상 문장을 잡지 않는지 고정한다."""
        for text in ("(75 tests)", "Ran 74 tests", "현재 전체 **74개**다", "검사 75개",
                     "테스트는 40개이며", "112개 테스트", "근거 원장 59건", "commit 63"):
            with self.subTest(text=text):
                self.assertRegex(text, RESTATED_COUNT)
        for text in ("# v0.1 계약 25개", "F01–F29는 29개의 독립 실험이 아니다",
                     "검토 기록은 시간순으로 다섯이다", "Python 3.12/3.13"):
            with self.subTest(text=text):
                self.assertNotRegex(text, RESTATED_COUNT)

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

    def test_encoding_check_rejects_control_characters(self):
        """스크립트로 문서를 고치다 '\\b'가 백스페이스가 되어 경로 글자가 사라진 일이 있었다."""
        import tempfile
        from tools.check_encoding import problems

        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp, "broken.md")
            broken.write_bytes("첫 줄\n경로 ~\\.local".encode("utf-8") + bytes([0x08]) + b"in\n")
            found = problems([broken])
            self.assertEqual(len(found), 1)
            self.assertIn(":2:", found[0])
            self.assertIn("0x08", found[0])
            self.assertNotIn(chr(0x08), found[0])
            fine = Path(tmp, "fine.md")
            fine.write_bytes("탭\t과 CRLF\r\n정상\n".encode("utf-8"))
            self.assertEqual(problems([fine]), [])

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
