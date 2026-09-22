"""Offline reference integrity; does not verify external sources or their truth."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

from tools.validate_v02 import strict_load

ROOT = Path(__file__).resolve().parents[1]
REGISTRIES = (
    ("v0.3", "E", range(1, 32), range(1, 10), "04-decisions-and-evaluation.md"),
    ("v0.4", "F", range(1, 22), range(10, 19), "02-frontier-architecture.md"),
)


def evidence_ids(text):
    def expand(match):
        prefix, start, end = match.groups()
        return "/".join(f"{prefix}{i:02}" for i in range(int(start), int(end) + 1))
    text = re.sub(r"([EF])(\d{2})[\u2013-](?:[EF])?(\d{2})", expand, text)
    return set(re.findall(r"\b[EF]\d{2}\b", text))


class ResearchIntegrityTests(unittest.TestCase):
    def test_registry_ids_and_decisions(self):
        for version, prefix, numbers, decisions, _ in REGISTRIES:
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

    def test_adr_and_registry_mappings_are_bidirectional(self):
        for version, _, _, decisions, filename in REGISTRIES:
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

    def test_markdown_relative_link_targets_exist(self):
        # Inline Markdown file links only; external URLs and heading anchors are not checked.
        paths = list(ROOT.glob("*.md"))
        for folder in ("docs", "contracts"):
            paths.extend((ROOT / folder).rglob("*.md"))
        for path in paths:
            content = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
            for target in re.findall(r"\[[^\]\n]*\]\(([^)\s]+)\)", content):
                parts = urlsplit(target)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                with self.subTest(path=path.relative_to(ROOT), target=target):
                    self.assertTrue((path.parent / unquote(parts.path)).exists())


if __name__ == "__main__":
    unittest.main()
