"""쌓임 방지(docs/COLLABORATION.md 7절). 크기 상한과 도구의 사용처만 본다 — 내용이 옳은지는 보지 않는다.

2026-09-25 정리에서 본 쌓임은 모두 더하는 사람은 있고 빼는 사람은 없는 모양이었다. 인계 문서는
세션마다 한 일을 덧붙여 되풀이해 불었고, 끝난 일회성 도구는 그 도구만 시험하는 테스트 때문에 쓰이는
것처럼 보였다. 상한에 걸리면 상한을 올리지 말고 이력·끝난 일·다른 곳에 있는 사실을 뺀다.
"""
from datetime import date
from pathlib import Path
import re
import unittest

from test_research_integrity import LIVING_DOCS

ROOT = Path(__file__).resolve().parents[1]

# 문서마다 글자 수 상한. 이 검사를 들인 PR #84가 줄인 뒤 크기의 약 1.3배다. 올려야 하면 PR 본문에 이유를 적는다.
# 목록 README(docs/reviews 등)는 기록마다 한 줄씩 느는 것이 정상이라 넣지 않는다.
BUDGETS = {
    "NEXT-SESSION.md": 18000,
    "AGENTS.md": 13000,
    "docs/COLLABORATION.md": 13000,
}

# 도구를 실제로 쓰는 곳: 코드·CI·설계 폴더와 살아 있는 문서. 테스트·자기 폴더 README·날짜 기록은 쓰는 곳이
# 아니다 — 지난 정리에서 지운 도구들은 바로 그것들 때문에 살아 있어 보였다. 날짜 기록의 목록 README와
# print_code_hashes.py(해시를 찍을 파일 목록)도 가리킬 뿐 쓰지 않으므로 뺀다. 이름만 적는 살아 있는 안내가
# 있으면 여전히 쓰는 곳으로 센다 — 지난 정리의 codex_account.py(app/README.md가 이름을 적은 얇은 래퍼)는 이
# 검사로 잡히지 않았을 것이다. 검사는 문자열을 볼 뿐 실제로 실행되는지는 모른다.
USER_FOLDERS = ("app/", "core/", "tools/", "design/", ".github/", ".githooks/")
USER_DOCS = LIVING_DOCS
NOT_USERS = ("tools/print_code_hashes.py", "docs/reviews/README.md", "docs/handoff/README.md")
TEXT = (".py", ".md", ".ps1", ".sh", ".yml", ".yaml", ".json", ".html", ".js")

# 두 예외 목록은 유예이지 보관이 아니다. 항목마다 (결정 날짜, 이유와 정할 카드)를 적고, 날짜가 지나면 실패한다.
# 미루려면 새 날짜와 이유를 PR에 적는다.

# 날짜 기록 폴더에 있지만 지금도 따라 하는 절차. 다시 따라 할 절차는 살아 있는 문서로 옮기는 것이 원칙이다
# (7절) — 옮기기 전까지만 여기에 적고, 옮기면 뺀다.
PROCEDURES = {
    "docs/experiments/v04-01-inventory/README.md":
        ("2026-10-25", "AGENTS.md가 설치·권한 재조사 절차로 지정한다 — 카드 #82에서 살아 있는 문서로 옮긴다"),
}

# 쓰는 곳은 없지만 지우지 않고 남기는 도구. 비어 있는 것이 정상이다.
KEPT: dict[str, tuple[str, str]] = {}


def tools():
    for path in sorted((ROOT / "tools").rglob("*")):
        if path.is_file() and path.name != "README.md" and "__pycache__" not in path.parts:
            yield path.relative_to(ROOT).as_posix()


def counts_as_user(name):
    return (name.startswith(USER_FOLDERS) or name in USER_DOCS or name in PROCEDURES) and name not in NOT_USERS


def user_texts():
    found = [ROOT / name for name in (*USER_DOCS, *PROCEDURES)]
    for folder in USER_FOLDERS:
        found.extend(path for path in (ROOT / folder).rglob("*")
                     if path.is_file() and path.suffix in TEXT and "__pycache__" not in path.parts)
    return {path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8", errors="replace").replace("\\", "/")
            for path in found if counts_as_user(path.relative_to(ROOT).as_posix())}


def references(tool, texts):
    """tool을 부르거나 가리키는 파일들. 경로, 모듈 이름, from-import, 같은 폴더의 도구가 부르는 파일 이름."""
    path = Path(tool)
    folder = path.parent.as_posix()
    module = path.with_suffix("").as_posix().replace("/", ".")
    patterns = [re.escape(tool), rf"\b{re.escape(module)}\b",
                rf"from\s+{re.escape(folder.replace('/', '.'))}\s+import\s+[^\n]*\b{re.escape(path.stem)}\b"]
    sibling = re.compile(rf"(?<![\w/.-]){re.escape(path.name)}\b")
    users = set()
    for name, text in texts.items():
        if name in (tool, f"{folder}/README.md"):
            continue
        if any(re.search(p, text) for p in patterns):
            users.add(name)
        elif Path(name).parent.as_posix() == folder and sibling.search(text):
            users.add(name)
    return users


def alive_tools(kept=None):
    """쓰는 곳이 있는 도구. 다른 도구만 쓰는 도구는 그 도구가 살아 있을 때만 산다."""
    texts = user_texts()
    users = {tool: references(tool, texts) for tool in tools()}
    alive = set(KEPT if kept is None else kept)
    grew = True
    while grew:
        grew = False
        for tool, found in users.items():
            if tool not in alive and any(not u.startswith("tools/") or u.endswith("/README.md") or u in alive
                                         for u in found):
                alive.add(tool)
                grew = True
    return users, alive


class AccumulationTests(unittest.TestCase):
    def test_living_rule_and_handoff_documents_stay_within_their_budget(self):
        for name, limit in BUDGETS.items():
            size = len((ROOT / name).read_text(encoding="utf-8"))
            with self.subTest(doc=name):
                self.assertLessEqual(
                    size, limit,
                    f"{name} is {size} characters, over its budget of {limit}. Move history to pull requests, "
                    "git and dated records, drop finished items and facts that already live elsewhere "
                    "(docs/COLLABORATION.md section 7). Raise the budget only with a reason in the pull request.")

    def test_handoff_names_only_the_pull_request_that_brought_it(self):
        """3절에는 진행 중인 일과 이 판을 들인 PR 하나만 둔다. 앞 PR을 줄줄이 적으면 인계가 다시 분다."""
        text = (ROOT / "NEXT-SESSION.md").read_text(encoding="utf-8")
        section = text.split("\n## 3. ", 1)[1].split("\n## 4. ", 1)[0]
        lines = [line for line in section.splitlines() if line.startswith("- **이 판을 들인 PR:**")]
        self.assertEqual(len(lines), 1, "section 3 needs exactly one '- **이 판을 들인 PR:**' line")
        self.assertEqual(len(re.findall(r"/pull/\d+", lines[0])), 1,
                         "that line links only its own pull request; earlier ones are in the PR list and git")

    def test_every_tool_has_a_current_user(self):
        users, alive = alive_tools()
        for tool in users:
            with self.subTest(tool=tool):
                if tool not in alive:
                    self.fail(f"{tool}: nothing current uses it (app, core, CI, another live tool, a living document "
                              "or a procedure). Its own tests and README do not count. Delete it, or add it to KEPT "
                              "with the reason and the card that decides it (docs/COLLABORATION.md section 7).")

    def test_the_exception_lists_do_not_outlive_their_reason(self):
        users, _ = alive_tools()
        texts = user_texts()
        for name, (deadline, reason) in (*KEPT.items(), *PROCEDURES.items()):
            with self.subTest(exception=name):
                self.assertTrue(re.search(r"#\d+", reason), f"{name}: name the card that decides it")
                self.assertGreaterEqual(
                    date.fromisoformat(deadline), date.today(),
                    f"{name} was to be decided by {deadline} ({reason}). Delete or move it now, or give a new date "
                    "and the reason in the pull request.")
        _, alive_without_exceptions = alive_tools(kept=())
        for tool in KEPT:
            with self.subTest(kept=tool):
                self.assertIn(tool, users, f"{tool} no longer exists; remove it from KEPT")
                self.assertNotIn(tool, alive_without_exceptions, f"{tool} has a current user now; remove it from KEPT")
        for doc in PROCEDURES:
            with self.subTest(procedure=doc):
                self.assertTrue((ROOT / doc).is_file(), f"{doc} is gone; remove it from PROCEDURES")
                self.assertTrue(any(doc in found for found in users.values()),
                                f"{doc} runs no tool; remove it from PROCEDURES")
        self.assertTrue(texts)

    def test_the_user_check_catches_what_the_last_cleanup_removed(self):
        """2026-09-25에 지운 일회성 도구는 자기 테스트·README·기록만 가리켰다. 그런 도구를 이 검사가 잡는지 고정한다.
        (그 정리 직전 저장소에 돌리면 지운 일곱 가운데 여섯을 잡는다.)"""
        texts = {
            "tests/test_w2_codex_sandbox.py": "from tools.w2 import codex_sandbox",
            "tools/w2/README.md": "| [`codex_sandbox.py`](codex_sandbox.py) | K12 |",
            "docs/reviews/2026-09-24-x/README.md": "python3 tools/w2/codex_sandbox.py",
            "docs/reviews/README.md": "| [K12](2026-09-24-x/README.md) | `tools/w2/codex_sandbox.py` |",
            "tools/print_code_hashes.py": '"tools/w2/codex_sandbox.py",',
            "tools/w2/codex_profile.py": "import json",
        }

        def users(found):
            return references("tools/w2/codex_sandbox.py", {k: v for k, v in found.items() if counts_as_user(k)})

        self.assertEqual(users(texts), set())
        texts["app/cli_executor.py"] = "from tools.w2 import observe, codex_sandbox"
        texts["tools/w2/codex_profile.py"] = "subprocess.run([sys.executable, 'codex_sandbox.py'])"
        self.assertEqual(users(texts), {"app/cli_executor.py", "tools/w2/codex_profile.py"})


if __name__ == "__main__":
    unittest.main()
