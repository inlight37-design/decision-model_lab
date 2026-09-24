"""app.cli_executor 검사(인계 N1). 실제 CLI·모델은 부르지 않는다.

가짜 `claude`·`codex` 실행 파일을 설치된 모양 그대로(~/.local/bin의 링크 → 버전 폴더의 실행 파일) 임시 HOME에
만들고, 실행기의 실제 경로(env.resolve → build_spec → isolation.run → interpret)와 controller의 수용 관문으로
돌린다. 격리 경로는 bubblewrap을 쓸 수 있는 Linux에서만 돈다. 시작 전 거절은 어느 플랫폼에서나 본다.
"""
from datetime import date
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from app import cli_executor, controller as c
from app.cli_executor import CliExecutor
from app.store import Store, events
from core import adapters, isolation, runner


def bwrap_usable():
    """test_core_isolation과 같은 판정: 신뢰한 bwrap이 있고 실제로 namespace를 만들 수 있는 Linux."""
    if sys.platform != "linux" or not (os.path.exists(isolation.BWRAP) and os.path.exists("/usr/bin/python3")):
        return False
    probe = [isolation.BWRAP, "--unshare-all", "--share-net", "--die-with-parent", "--ro-bind", "/usr", "/usr",
             "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
             "--proc", "/proc", "--", "/usr/bin/true"]
    return subprocess.run(probe, capture_output=True, check=False).returncode == 0


# 가짜 CLI. 받은 argv를 확인하고, stdin으로 받은 질문의 크기와 격리 안에서 보이는 설정 폴더를 답에 적는다.
FAKE = r'''#!/usr/bin/python3
import json, os, sys, time
FLAVOR, BEHAVIOR, OWN = {flavor!r}, {behavior!r}, {own!r}
argv = sys.argv[1:]
question = sys.stdin.read()
if FLAVOR == "claude" and not ("-p" in argv and argv[argv.index("--output-format") + 1] == "stream-json"):
    sys.exit(3)
if FLAVOR == "codex" and not (argv[0] == "exec" and "--json" in argv and argv[-1] == "-"):
    sys.exit(3)
home = os.environ["HOME"]
# K46: 격리 안의 HOME 기준으로 로그인 파일만 읽기 금지하는 권한 profile. 옛 --sandbox와 섞지 않는다
deny = '"' + os.path.join(home, ".codex", "auth.json") + '" = "deny"'
if FLAVOR == "codex" and ("--sandbox" in argv or 'default_permissions="dml-discussant"' not in argv
                          or not any(deny in a for a in argv)):
    sys.exit(4)
with open(os.path.join(home, OWN, "fake-was-here"), "w") as f:
    f.write("1")
if BEHAVIOR == "slow":
    time.sleep(3)
model = argv[argv.index("--model") + 1]
seen = {{name: os.path.lexists(os.path.join(home, name)) for name in (".claude", ".claude.json", ".codex")}}
text = json.dumps({{"question_bytes": len(question.encode()), "seen": seen,
                   "question_in_argv": any(question.strip()[:20] in a for a in argv)}}, sort_keys=True)
if BEHAVIOR.startswith("flood"):
    sys.stderr.write("n" * 70000 + ("rejected: blocked by policy" if BEHAVIOR == "flood-rejected" else ""))
if FLAVOR == "claude":
    print(json.dumps({{"type": "system", "subtype": "init", "tools": [],
                      "permissionMode": "dontAsk", "mcp_servers": []}}))
    print(json.dumps({{"type": "result", "is_error": False, "result": text, "modelUsage": {{model: {{}}}},
                      "usage": {{"input_tokens": 1, "output_tokens": 1}}, "permission_denials": []}}))
else:
    print(json.dumps({{"type": "item.completed", "item": {{"type": "agent_message", "text": text}}}}))
    print(json.dumps({{"type": "turn.completed", "usage": {{"input_tokens": 1, "output_tokens": 1}}}}))
'''


def install(home: Path, flavor: str, behavior: str = "ok") -> None:
    """설치된 모양: ~/.local/bin/<flavor> → 버전 폴더의 실행 파일. 자기 설정 폴더도 만든다."""
    if flavor == "claude":
        target, own = home / ".local/share/claude/versions/9.9.9", ".claude"
        (home / ".claude.json").write_text("{}", encoding="utf-8")
    else:
        target, own = home / ".local/share/codex/releases/9.9.9/bin/codex", ".codex"
    (home / own).mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(FAKE.format(flavor=flavor, behavior=behavior, own=own), encoding="utf-8")
    target.chmod(0o755)
    link = home / ".local/bin" / flavor
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink():
        link.unlink()
    link.symlink_to(target)


def claude(pid="claude"):
    return c.ParticipantSpec(pid, "Claude Code", "anthropic", c.CLI, "claude-code", "claude-test-9")


def codex(pid="codex"):
    return c.ParticipantSpec(pid, "Codex", "openai", c.CLI, "codex", "gpt-test-9")


class Base(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dml-n1-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.home = self.root / "home"
        self.home.mkdir()
        self.store = Store(self.root / "ledger" / "journal.db")
        self.addCleanup(self.store.close)

    def executor(self, **kwargs):
        return CliExecutor(never=(str(self.root / "ledger"),), unchecked=True, home=str(self.home),
                           base_env={"PATH": f"{self.home}/.local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"}, **kwargs)

    def controller(self, executor, **kwargs):
        return c.Controller(self.store, executor, work_root=str(self.root / "work"), timeout=30, **kwargs)

    def run_view(self, ctl, run_id):
        return next(r for r in ctl.view()["runs"] if r["run_id"] == run_id)

    def parts(self, ctl, run_id):
        return {p["pid"]: p for p in self.run_view(ctl, run_id)["participants"]}


class RefusedBeforeStartTests(Base):
    """어느 플랫폼에서나 돈다. 실행 파일이 없으면 프로세스를 만들지 않고 failed_to_start로 끝난다."""

    def test_nothing_starts_when_the_cli_cannot_be_planned(self):
        ex = CliExecutor(never=(str(self.root / "ledger"),), unchecked=True, home=str(self.home),
                         base_env={"PATH": str(self.home)})
        with self.assertRaises(cli_executor.REFUSED_BEFORE_START):
            ex.plan(claude(), "질문", str(self.root))
        agy = c.ParticipantSpec("g", "agy", "google", c.CLI, "antigravity", "m")
        with self.assertRaisesRegex(adapters.AdapterError, "not run by the CLI executor"):
            ex.plan(agy, "질문", str(self.root))
        ctl = self.controller(ex)
        run_id = ctl.create_run("질문", [claude()], min_independent=1)
        self.assertTrue(ctl.wait_idle())
        part = self.parts(ctl, run_id)["claude"]
        self.assertEqual((part["state"], part["status"]), (c.REJECTED, "process_failed_to_start"))
        self.assertIs(part["result"]["tree_confirmed_empty"], True)     # 시작한 것이 없다 — unknown이 아니다
        started = next(e for e in events(self.store, run_id) if e["kind"] == "attempt_started")
        self.assertIn("refused", started["spec"])
        self.assertEqual((started["execution"], part["execution"]), ("real", "real"))

    def test_revoked_inventory_between_plan_and_run_starts_nothing(self):
        exe = str(self.root / "versions" / "9.9.9")
        with mock.patch.object(cli_executor.core_env, "resolve", return_value=exe):
            revision = self.executor().plan(claude(), "question", str(self.root)).revision
            seen = {"status": "observed", "observed_at": date.today().isoformat(), "evidence": "synthetic"}
            observed = {**seen, "spec_revision": revision}
            row = {"adapter_id": "claude-code", "installed": {**seen, "version": "9.9.9"},
                   "auth_observed": {**seen, "auth_mode": "subscription_oauth", "funding_mode": "subscription"},
                   "transport_observed": observed, "context_conformance": observed,
                   "permission_conformance": observed}
            path = self.root / "inventory.json"
            manifest = {"schema": "runtime-inventory/2", "adapters": [row]}
            path.write_text(json.dumps(manifest), encoding="utf-8")
            executor = self.executor(inventory=path)
            planned = executor.plan(claude(), "question", str(self.root))
        row["permission_conformance"] = {"status": "unknown"}
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with mock.patch.object(isolation, "run") as start:
            result, outcome = executor.run(planned, 5)
        start.assert_not_called()
        self.assertEqual(result.state, runner.FAILED_TO_START)
        self.assertIn("permission_conformance is unknown", result.error)
        self.assertFalse(outcome.ok)


@unittest.skipUnless(bwrap_usable(), "bubblewrap을 쓸 수 있는 Linux에서만")
class RealPathTests(Base):
    """실제 격리 경로. 가짜 CLI를 쓰므로 모델은 부르지 않는다."""

    def test_both_clis_run_isolated_and_pass_the_gate(self):
        install(self.home, "claude")
        install(self.home, "codex")
        ctl = self.controller(self.executor())
        question = "한글 질문과 --선행 대시"
        run_id = ctl.create_run(question, [claude(), codex()], min_independent=2)
        self.assertTrue(ctl.wait_idle(60))
        view = self.run_view(ctl, run_id)
        parts = self.parts(ctl, run_id)
        self.assertEqual(view["phase"], "revealed", parts)
        prompt_bytes = len(view["prompt"].encode("utf-8"))
        for pid, own, other in (("claude", ".claude", ".codex"), ("codex", ".codex", ".claude")):
            with self.subTest(pid=pid):
                part = parts[pid]
                self.assertEqual(part["state"], c.ACCEPTED, part)
                seen = json.loads(part["draft"])
                self.assertEqual(seen["question_bytes"], prompt_bytes)       # 질문이 stdin으로 다 갔다
                self.assertFalse(seen["question_in_argv"])                   # 명령줄에는 없다
                self.assertTrue(seen["seen"][own])                           # 자기 설정 폴더는 보이고
                self.assertFalse(seen["seen"][other])                        # 다른 CLI의 것은 안 보인다
                self.assertTrue((self.home / own / "fake-was-here").exists())  # 자기 폴더는 쓰기로 연결됐다
                result = part["result"]
                self.assertEqual((result["containment"], result["tree_confirmed_empty"], result["input_delivery"]),
                                 (runner.PID_NAMESPACE, True, runner.INPUT_COMPLETE))
        self.assertTrue(parts["claude"]["result"]["model_match"])
        self.assertIsNone(parts["codex"]["result"]["model_match"])        # Codex는 모델을 알리지 않는다(K32)
        records = [e["spec"] for e in events(self.store, run_id) if e["kind"] == "attempt_started"]
        self.assertEqual(len(records), 2)
        for record in records:
            self.assertEqual((record["input_via"], record["input_sha256"]), (adapters.STDIN, view["input_sha256"]))
            self.assertNotIn(question, json.dumps(record, ensure_ascii=False))  # 기록에 질문 본문이 없다
        codex_argv = next(r["argv"] for r in records if r["adapter_id"] == "codex")
        self.assertEqual([codex_argv[i + 1] for i, a in enumerate(codex_argv) if a == "-c"],
                         list(adapters.codex_permissions(os.path.realpath(self.home))))  # K46 profile이 기록에도 남는다

    def test_codex_rejections_are_counted_past_the_output_cap(self):
        """K02. 보관 상한을 넘긴 stderr 뒤쪽의 거절 표식도 센다. 표식이 없으면 잘렸어도 받는다."""
        for behavior, state, status in (("flood-rejected", c.REJECTED, "tools_rejected"),
                                        ("flood", c.ACCEPTED, "ok")):
            with self.subTest(behavior=behavior):
                install(self.home, "codex", behavior)
                ctl = self.controller(self.executor(max_output_bytes=1000))
                run_id = ctl.create_run("질문", [codex()], min_independent=1)
                self.assertTrue(ctl.wait_idle(60))
                part = self.parts(ctl, run_id)["codex"]
                self.assertEqual((part["state"], part["status"]), (state, status), part)

    def test_a_record_gates_every_attempt(self):
        """N4. 기록의 다섯 칸이 모두 관측됐고 설치 버전이 같을 때만 부른다. 아니면 프로세스를 만들기 전에 거절한다."""
        install(self.home, "claude")
        seen = {"status": "observed", "observed_at": "2026-09-23", "evidence": "synthetic"}
        # 참여자 계획의 판으로 본 칸(리뷰 R04, core.contract). 계획은 기록 없이 같은 HOME·PATH로 만든다
        spec = {**seen, "spec_revision": self.executor().plan(claude(), "질문", str(self.root / "w")).revision}
        row = {"adapter_id": "claude-code", "installed": {**seen, "version": "9.9.9"},
               "auth_observed": {**seen, "auth_mode": "subscription_oauth", "funding_mode": "subscription"},
               "transport_observed": spec, "context_conformance": spec, "permission_conformance": spec}
        path = self.root / "inventory.json"
        path.write_text(json.dumps({"schema": "runtime-inventory/2", "host": {"label": "t"}, "adapters": [row]}))
        ex = CliExecutor(never=(str(self.root / "ledger"),), inventory=path, home=str(self.home),
                         base_env={"PATH": f"{self.home}/.local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"})
        with mock.patch.object(cli_executor, "date") as fake_date:
            fake_date.today.return_value = date(2026, 9, 23)
            ctl = self.controller(ex)
            first = ctl.create_run("질문", [claude()], min_independent=1)
            self.assertTrue(ctl.wait_idle(60))
            self.assertEqual(self.parts(ctl, first)["claude"]["state"], c.ACCEPTED)
            row["permission_conformance"] = {"status": "unknown"}
            path.write_text(json.dumps({"schema": "runtime-inventory/2", "host": {"label": "t"}, "adapters": [row]}))
            second = ctl.create_run("다음 질문", [claude()], min_independent=1)
            self.assertTrue(ctl.wait_idle(60))
        part = self.parts(ctl, second)["claude"]
        self.assertEqual((part["state"], part["status"]), (c.REJECTED, "process_failed_to_start"))
        self.assertIn("not eligible to run: permission_conformance is unknown", part["detail"])

    def test_a_late_result_after_a_restart_is_ignored_on_the_real_path(self):
        """늦은 결과는 실제 실행기에서도 반영하지 않는다(A1-03). 시도는 끝까지 돌고 종료가 확인된다."""
        install(self.home, "claude", "slow")
        first = self.controller(self.executor())
        run_id = first.create_run("질문", [claude()], min_independent=1)
        time.sleep(0.5)
        second = self.controller(self.executor())                   # 같은 원장으로 다시 시작
        self.assertEqual(self.parts(second, run_id)["claude"]["state"], c.UNKNOWN)
        self.assertTrue(first.wait_idle(60))
        self.assertEqual(self.parts(second, run_id)["claude"]["state"], c.UNKNOWN)
        ignored = next(e for e in events(self.store, run_id) if e["kind"] == "attempt_result_ignored")
        self.assertIs(ignored["result"]["tree_confirmed_empty"], True)
        self.assertIsNone(self.store.row("SELECT 1 FROM drafts WHERE run_id = ?", run_id))


if __name__ == "__main__":
    unittest.main()
