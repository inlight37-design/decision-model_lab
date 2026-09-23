"""tools/w2/observe.py 검사(인계 N2). 실제 CLI·모델은 부르지 않는다.

승인·상한·멈춤 규칙은 어느 플랫폼에서나 본다. 호출은 가짜 `claude`·`codex`(stream-json·잘못된 값 거절까지
흉내)를 설치된 모양 그대로 만들어 실제 격리 경로로 돌린다 — bubblewrap을 쓸 수 있는 Linux에서만.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from app.cli_executor import CliExecutor
from core import adapters, isolation
from tools.w2 import observe


def bwrap_usable():
    if sys.platform != "linux" or not (os.path.exists(isolation.BWRAP) and os.path.exists("/usr/bin/python3")):
        return False
    probe = [isolation.BWRAP, "--unshare-all", "--share-net", "--die-with-parent", "--ro-bind", "/usr", "/usr",
             "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
             "--proc", "/proc", "--", "/usr/bin/true"]
    return subprocess.run(probe, capture_output=True, check=False).returncode == 0


FAKE = r'''#!/usr/bin/python3
import json, os, re, sys
FLAVOR, BEHAVIOR = {flavor!r}, {behavior!r}
argv = sys.argv[1:]
question = sys.stdin.read()
def opt(name):
    return argv[argv.index(name) + 1] if name in argv else None
if FLAVOR == "claude" and opt("--permission-mode") == "notamode" and BEHAVIOR != "ignore-invalid":
    sys.stderr.write("error: option '--permission-mode <mode>' argument 'notamode' is invalid.\n")
    sys.exit(1)
if FLAVOR == "codex" and opt("--sandbox") == "notamode":
    sys.stderr.write("error: invalid value 'notamode' for '--sandbox <SANDBOX_MODE>'\n")
    sys.exit(2)
if FLAVOR == "claude":  # 실제 CLI처럼 자기 설정 폴더에 무언가 쓴다(관측 도구가 이름을 적는지 본다)
    with open(os.path.join(os.environ["HOME"], ".claude", "fake-state.json"), "w") as f:
        f.write("{{}}")
def first_line(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.readline().strip()
    except OSError as e:
        return "could not: " + type(e).__name__
if "Reply with exactly" in question:
    text = "OK"
else:
    allowed = re.search(r"Read the file (\S+) and quote", question).group(1)
    forbidden = re.search(r"Try to read the file (\S+) and", question).group(1)
    text = json.dumps({{"allowed": first_line(allowed), "forbidden": first_line(forbidden), "write": "no",
                       "instruction_markers": "none", "dash_line_seen": "- 이 줄은" in question}})
model = opt("--model")
usage = {{"input_tokens": len(question.encode()) // 4, "output_tokens": 3}}
if FLAVOR == "claude":
    result = {{"type": "result", "is_error": False, "result": text, "modelUsage": {{model: {{}}}}, "usage": usage,
              "permission_denials": []}}
    if opt("--output-format") == "stream-json":
        assert "--verbose" in argv
        print(json.dumps({{"type": "system", "subtype": "init", "model": model, "permissionMode": opt("--permission-mode"),
                          "apiKeySource": "none", "tools": ["Read"], "mcp_servers": [], "plugins": [],
                          "slash_commands": [], "cwd": os.getcwd(), "session_id": "fake"}}))
    print(json.dumps(result))
else:
    sys.stderr.write("codex sandbox: landlock unavailable, falling back\n")
    print(json.dumps({{"type": "item.completed", "item": {{"type": "command_execution", "command": "cat allowed.txt",
                                                           "exit_code": 0, "status": "completed"}}}}))
    print(json.dumps({{"type": "item.completed", "item": {{"type": "agent_message", "text": text}}}}))
    print(json.dumps({{"type": "turn.completed", "usage": usage}}))
'''


def install(home: Path, flavor: str, behavior: str = "ok") -> None:
    if flavor == "claude":
        target, own = home / ".local/share/claude/versions/9.9.9", ".claude"
        (home / ".claude.json").write_text("{}", encoding="utf-8")
    else:
        target, own = home / ".local/share/codex/releases/9.9.9/bin/codex", ".codex"
    (home / own).mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(FAKE.format(flavor=flavor, behavior=behavior), encoding="utf-8")
    target.chmod(0o755)
    link = home / ".local/bin" / flavor
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink():
        link.unlink()
    link.symlink_to(target)


class Base(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dml-observe-test-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.state = self.root / "state"

    def record(self, n, provider, probe, as_expected=None):
        observe._append(self.state, {"event": "started", "n": n, "provider": provider, "probe": probe, "model": "m"})
        if as_expected is not None:
            observe._append(self.state, {"event": "finished", "n": n, "as_expected": as_expected, "status": "x"})


class ApprovalTests(Base):
    """어느 플랫폼에서나 돈다. 승인 없이는 부르지 않고, 상한과 멈춤 규칙을 지킨다."""

    def test_nothing_is_called_without_an_approval_with_a_note(self):
        with self.assertRaisesRegex(observe.ObserveError, "no approval"):
            observe.check_allowed(self.state, "b1", False)
        with self.assertRaisesRegex(observe.ObserveError, "note"):
            observe.approve(self.state, {"claude": 1, "codex": 1}, 300, "  ")
        observe.approve(self.state, {"claude": 1, "codex": 0}, 300, "시험")
        with self.assertRaisesRegex(observe.ObserveError, "unknown probe"):
            observe.check_allowed(self.state, "b9", False)

    def test_caps_count_every_started_call_and_a_new_approval_opens_a_new_window(self):
        observe.approve(self.state, {"claude": 2, "codex": 0}, 300, "시험 승인")
        with self.assertRaisesRegex(observe.ObserveError, "cap of 0"):
            observe.check_allowed(self.state, "b2", False)
        self.record(1, "claude", "b1", True)
        self.record(2, "claude", "plain-claude", True)
        with self.assertRaisesRegex(observe.ObserveError, "cap of 2"):
            observe.check_allowed(self.state, "b1-combo", False)
        observe.approve(self.state, {"claude": 1, "codex": 0}, 300, "다음 승인")
        self.assertEqual(observe.check_allowed(self.state, "b1-combo", False)[1], "claude")
        self.assertEqual(observe.usage_state(self.state)["claude"]["used"], 0)

    def test_a_call_that_went_wrong_or_never_finished_stops_that_provider(self):
        observe.approve(self.state, {"claude": 5, "codex": 5}, 300, "시험 승인")
        self.record(1, "claude", "p3-claude", False)
        with self.assertRaisesRegex(observe.ObserveError, "did not go as expected"):
            observe.check_allowed(self.state, "b1", False)
        self.assertEqual(observe.check_allowed(self.state, "b1", True)[1], "claude")  # 원인을 본 뒤에만
        self.record(2, "codex", "b2")                                                # 시작만 있고 끝이 없다
        with self.assertRaisesRegex(observe.ObserveError, "did not go as expected"):
            observe.check_allowed(self.state, "plain-codex", False)

    def test_the_command_line_writes_the_approval_and_status(self):
        with mock.patch.object(observe, "STATE", self.state), mock.patch("sys.stdout"):
            self.assertEqual(observe.main(["approve", "--claude", "3", "--codex", "2", "--note", "사용자 승인"]), 0)
            self.assertEqual(observe.main(["status"]), 0)
            if sys.platform != "linux":
                self.assertEqual(observe.main(["call", "b1", "m"]), 2)          # Linux에서만 부른다
        self.assertEqual(observe.load_approval(self.state)["caps"], {"claude": 3, "codex": 2})


@unittest.skipUnless(bwrap_usable(), "bubblewrap을 쓸 수 있는 Linux에서만")
class CallTests(Base):
    """실제 격리 경로와 가짜 CLI. 모델은 부르지 않는다."""

    def setUp(self):
        super().setUp()
        self.home = self.root / "home"
        self.home.mkdir()
        install(self.home, "claude")
        install(self.home, "codex")

    def executor(self):
        return CliExecutor(never=(str(self.state),), unchecked=True, home=str(self.home),
                           base_env={"PATH": f"{self.home}/.local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"})

    def call(self, probe, **kwargs):
        return observe.call(self.state, probe, "claude-test-9" if "claude" in probe or probe.startswith("b1")
                            else "gpt-test-9", executor=self.executor(), **kwargs)

    def test_boundary_probes_run_isolated_and_are_summarized_without_the_raw_output(self):
        observe.approve(self.state, {"claude": 1, "codex": 1}, 60, "시험 승인")
        b1 = self.call("b1")
        self.assertTrue(b1["as_expected"], b1)
        self.assertEqual(b1["argv_changes"], ["--output-format stream-json --verbose"])
        self.assertEqual((b1["init"]["apiKeySource"], b1["init"]["tools"]), ("none", ["Read"]))
        answer = json.loads(json.loads((self.state / "results/001-b1.json").read_text(encoding="utf-8"))["answer"])
        self.assertTrue(answer["allowed"].startswith(observe.MARK["allowed"]))    # 공통 자료는 읽기 전용으로 보이고
        self.assertTrue(answer["forbidden"].startswith("could not"))            # 다른 참여자 초안은 안 보인다
        self.assertTrue(answer["dash_line_seen"])                               # 선행 대시 줄이 stdin으로 갔다
        self.assertEqual((b1["input_delivery"], b1["tree_confirmed_empty"]), ("complete", True))
        self.assertEqual(b1["config_changes"]["added"], ["~/.claude/fake-state.json"])  # CLI가 쓴 설정 파일 이름
        b2 = self.call("b2")
        self.assertTrue(b2["as_expected"], b2)
        self.assertEqual(b2["stderr_counts"], {adapters.CODEX_REJECTED: 0})
        self.assertEqual(b2["codex_items"][0]["type"], "command_execution")
        self.assertTrue(any("landlock" in line for line in b2["stderr_hints"]))
        self.assertNotIn(str(self.home), json.dumps([b1, b2], ensure_ascii=False))  # 요약에 HOME 경로를 쓰지 않는다
        with self.assertRaisesRegex(observe.ObserveError, "cap of 1"):
            self.call("plain-claude")
        kinds = [c["event"] for c in observe.calls(self.state)]
        self.assertEqual(kinds, ["started", "finished", "started", "finished"])   # 거절된 세 번째는 적지 않았다

    def test_invalid_values_must_be_refused_and_an_answer_stops_the_provider(self):
        observe.approve(self.state, {"claude": 3, "codex": 1}, 60, "시험 승인")
        self.assertTrue(self.call("p3-codex")["as_expected"])
        self.assertTrue(self.call("p3-claude")["as_expected"])
        install(self.home, "claude", "ignore-invalid")                          # 잘못된 값을 무시하고 답한다
        self.assertFalse(self.call("p3-claude")["as_expected"])
        with self.assertRaisesRegex(observe.ObserveError, "did not go as expected"):
            self.call("b1")

    def test_plan_shows_specs_and_mounts_without_calling(self):
        report = observe.plan(self.state, executor=self.executor(), model="m-9")
        self.assertEqual(set(report["probes"]), set(observe.PROVIDER))
        b1, plain = report["probes"]["b1"], report["probes"]["plain-claude"]
        self.assertIn("stream-json", b1["argv"])
        self.assertTrue(any(p.endswith("/input") for p in b1["read_only"]))    # 공통 자료
        self.assertFalse(any(p.endswith("/input") for p in plain["read_only"]))
        self.assertEqual(b1["never"], [str(self.state)])                        # 상태 폴더는 격리 밖
        self.assertNotIn("sandbox conformance", json.dumps(report))            # 질문 본문은 없다
        self.assertEqual(observe.calls(self.state), [])


if __name__ == "__main__":
    unittest.main()
