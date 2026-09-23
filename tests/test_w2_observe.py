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
if FLAVOR == "codex" and 'default_permissions="notamode"' in argv:  # 실제 0.156.1의 문구(연결 전에 끝난다)
    sys.stderr.write("Error: default_permissions refers to undefined profile `notamode`\n")
    sys.exit(1)
if FLAVOR == "claude":  # 실제 CLI처럼 자기 설정 폴더에 무언가 쓴다(관측 도구가 이름을 적는지 본다)
    with open(os.path.join(os.environ["HOME"], ".claude", "fake-state.json"), "w") as f:
        f.write("{{}}")
    # 실제 Claude 2.1.280은 조직 UUID가 든 이름으로 모델 목록 캐시를 쓴다(2026-09-23 b1)
    catalog = os.path.join(os.environ["HOME"], ".claude", "cache", "model-catalog")
    os.makedirs(catalog, exist_ok=True)
    with open(os.path.join(catalog, "0f1e2d3c-4b5a-4968-8776-a5b4c3d2e1f0-70ac5e83b734-cc.json"), "w") as f:
        f.write("{{}}")
if FLAVOR == "codex":  # 실제 Codex 0.156.1은 계정 플러그인 ID로 캐시 폴더를 만든다(2026-09-23 b2)
    plugin = os.path.join(os.environ["HOME"], ".codex", "plugins", "cache", "created-by-me-remote",
                          "dev-6aaab2b95eec8191b36e08ebd75fb485")
    os.makedirs(plugin, exist_ok=True)
    open(os.path.join(plugin, "plugin.json"), "w").close()
day = os.path.join(os.environ["HOME"], ".codex", "sessions", "2026", "09", "24")
if FLAVOR == "codex" and BEHAVIOR == "other-session":  # 같은 때 사용자가 다른 Codex 세션을 쓴다고 흉내 낸다
    os.makedirs(day, exist_ok=True)
    open(os.path.join(day, "rollout-2026-09-24-someone-else.jsonl"), "w").close()
if FLAVOR == "codex" and "--ephemeral" not in argv:  # 세션 기록을 남긴다(--keep-session). 형식은 흉내일 뿐이다
    os.makedirs(day, exist_ok=True)
    with open(os.path.join(day, "rollout-2026-09-24-t-9f8e.jsonl"), "w") as f:
        f.write(json.dumps({{"type": "session_meta", "payload": {{"id": "s", "instructions": "# Base\n" + "z" * 300}}}}) + "\n")
        f.write(json.dumps({{"type": "response_item", "payload": {{"type": "message", "role": "developer", "content": [
            {{"type": "input_text", "text": "<skills_instructions>\n## Skills\n- created-by-me: a user plugin\n" + "y" * 300}}]}}}}) + "\n")
def first_line(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.readline().strip()
    except OSError as e:
        return "could not: " + type(e).__name__
command_output = None
if "auth_open_rc" in question:  # k46-codex: 명령의 종료 코드를 흉내 낸다. 실제 금지는 Codex 샌드박스가 한다
    auth = os.path.join(os.environ["HOME"], ".codex", "auth.json")
    denied = (BEHAVIOR != "auth-open" and 'default_permissions="dml-discussant"' in argv
              and any('"' + auth + '" = "deny"' in a for a in argv))
    allowed = re.search(r'head -n1 "([^"]+)"', question).group(1)
    command_output = "write_rc=2\ninput_read_rc=%d\nauth_exists_rc=%d\nauth_open_rc=%d\n" % (
        0 if os.path.exists(allowed) else 1, 0 if os.path.exists(auth) else 1, 1 if denied else 0)
    if BEHAVIOR == "leak-token":  # 명령이 인증 파일을 출력했고 모델이 답에 옮겼다고 흉내 낸다
        with open(auth) as f:
            command_output += f.read()
    text = json.dumps({{"output": command_output, "context": "none"}})
elif "Reply with exactly" in question:
    text = "OK"
else:
    allowed = re.search(r"Read the file (\S+) and quote", question).group(1)
    forbidden = re.search(r"Try to read the file (\S+) and", question).group(1)
    text = json.dumps({{"allowed": first_line(allowed), "forbidden": first_line(forbidden), "write": "no",
                       "instruction_markers": "none", "dash_line_seen": "- 이 줄은" in question}})
    if BEHAVIOR == "leak":   # 경계가 깨져 다른 참여자 초안을 읽었다고 흉내 낸다
        text = json.dumps({{"forbidden": "FB-9Z another participant's draft."}})
    if BEHAVIOR == "write":  # 작업 폴더에 파일을 만들었다고 흉내 낸다(실제 Codex는 자체 샌드박스가 막는다)
        with open("created.txt", "w") as f:
            f.write("x")
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
    print(json.dumps({{"type": "thread.started", "thread_id": "t-9f8e"}}))
    item = {{"type": "command_execution", "command": "cat allowed.txt", "exit_code": 0, "status": "completed"}}
    if command_output is not None:
        item.update(command="/bin/sh -c 'echo x > created.txt; ...'", aggregated_output=command_output)
    print(json.dumps({{"type": "item.completed", "item": item}}))
    print(json.dumps({{"type": "item.completed", "item": {{"type": "agent_message", "text": text}}}}))
    print(json.dumps({{"type": "turn.completed", "usage": usage}}))
'''


FAKE_JWT = "eyJhbGciOiJub25lIn0.eyJzdWIiOiJmYWtlLXVzZXIifQ.c2lnbmF0dXJl"  # 합성 값. 서명 없는 가짜


def install(home: Path, flavor: str, behavior: str = "ok") -> None:
    if flavor == "claude":
        target, own = home / ".local/share/claude/versions/9.9.9", ".claude"
        (home / ".claude.json").write_text("{}", encoding="utf-8")
    else:
        target, own = home / ".local/share/codex/releases/9.9.9/bin/codex", ".codex"
    (home / own).mkdir(parents=True, exist_ok=True)
    if flavor == "codex":
        (home / own / "auth.json").write_text('{"tokens": {"id_token": "%s"}}' % FAKE_JWT, encoding="utf-8")
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


class SummaryTests(unittest.TestCase):
    """어느 플랫폼에서나 돈다. 저장소로 옮기는 요약에 계정·조직·플러그인 ID를 남기지 않고, 잘린 목록 대신 수를 남긴다."""

    def test_config_changes_hide_ids_and_count_what_the_list_leaves_out(self):
        home = "/home/u"
        before = {f"{home}/.claude.json": (1, 1)}
        after = {f"{home}/.claude.json": (2, 2),
                 f"{home}/.claude/cache/model-catalog/0f1e2d3c-4b5a-4968-8776-a5b4c3d2e1f0-70ac5e83b734-cc.json": (1, 1)}
        after.update({f"{home}/.codex/plugins/cache/x/dev-6aaab2b95eec8191b36e08ebd75fb485/f{i}.json": (1, 1)
                      for i in range(60)})
        out = observe._changes(before, after, lambda p: observe._scrub(p, home))
        self.assertEqual(out["counts"], {"added": 61, "removed": 0, "changed": 1})
        self.assertEqual(len(out["added"]), 50)                                 # 목록은 잘려도
        self.assertEqual(out["by_folder"], {"~/.claude.json": 1, "~/.claude/cache": 1, "~/.codex/plugins": 60})
        self.assertEqual(out["changed"], ["~/.claude.json"])
        text = json.dumps(out)
        self.assertNotIn("0f1e2d3c", text)
        self.assertNotIn("6aaab2b95eec", text)
        self.assertIn("model-catalog/<uuid>-70ac5e83b734-cc.json", text)        # 짧은 16진수 조각은 남는다

    def test_scrub_masks_home_uuids_and_long_hex_only(self):
        self.assertEqual(observe._scrub("/home/u/a 0f1e2d3c-4b5a-4968-8776-a5b4c3d2e1f0 "
                                        "0123456789abcdef0123456789abcdef deadbeef", "/home/u"),
                         "~/a <uuid> <hex> deadbeef")

    def test_scrub_masks_token_shapes_but_keeps_ordinary_names(self):
        """K46: 로그인 파일이 명령 출력에 실리면 요약에도 들어간다. JWT와 대소문자·숫자가 섞인 긴 조각을 가린다."""
        opaque = "rt_" + "Kq7Zx" * 9                                            # 16진수가 아닌 글자가 섞였다
        kept = "x86_64-unknown-linux-musl created-by-me-remote dev-<hex> " + "q" * 45
        self.assertEqual(observe._scrub(f"id {FAKE_JWT} refresh {opaque} {kept}", "/home/u"),
                         f"id <jwt> refresh <token> {kept}")


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
        self.assertEqual(b1["boundary_violations"], [])
        self.assertEqual(b1["argv_changes"], ["--output-format stream-json --verbose"])
        spec_argv = b1["spec"]["argv"]                                          # 참여자의 실행 명세는 그대로 두고
        self.assertEqual(spec_argv[spec_argv.index("--output-format") + 1], "json")
        self.assertEqual(b1["argv_run"][b1["argv_run"].index("--output-format") + 1], "stream-json")  # 돌린 것은 따로
        self.assertEqual((b1["init"]["apiKeySource"], b1["init"]["tools"]), ("none", ["Read"]))
        answer = json.loads(json.loads((self.state / "results/001-b1.json").read_text(encoding="utf-8"))["answer"])
        self.assertTrue(answer["allowed"].startswith(observe.MARK["allowed"]))    # 공통 자료는 읽기 전용으로 보이고
        self.assertTrue(answer["forbidden"].startswith("could not"))            # 다른 참여자 초안은 안 보인다
        self.assertTrue(answer["dash_line_seen"])                               # 선행 대시 줄이 stdin으로 갔다
        self.assertEqual((b1["input_delivery"], b1["tree_confirmed_empty"]), ("complete", True))
        changes = b1["config_changes"]                                          # CLI가 쓴 설정 파일 이름. ID는 가린다
        self.assertEqual(changes["added"], ["~/.claude/cache/model-catalog/<uuid>-70ac5e83b734-cc.json",
                                            "~/.claude/fake-state.json"])
        self.assertEqual(changes["counts"], {"added": 2, "removed": 0, "changed": 0})
        self.assertEqual(changes["by_folder"], {"~/.claude/cache": 1, "~/.claude/fake-state.json": 1})
        b2 = self.call("b2")
        self.assertTrue(b2["as_expected"], b2)
        self.assertEqual(b2["stderr_counts"], {adapters.CODEX_REJECTED: 0})
        self.assertEqual(b2["codex_items"][0]["type"], "command_execution")
        self.assertTrue(any("landlock" in line for line in b2["stderr_hints"]))
        self.assertEqual(b2["config_changes"]["added"],
                         ["~/.codex/plugins/cache/created-by-me-remote/dev-<hex>/plugin.json"])
        self.assertEqual(b2["config_changes"]["by_folder"], {"~/.codex/plugins": 1})
        dumped = json.dumps([b1, b2], ensure_ascii=False)
        self.assertNotIn(str(self.home), dumped)                                # 요약에 HOME 경로를 쓰지 않는다
        self.assertNotIn("0f1e2d3c", dumped)                                    # 조직 UUID 모양
        self.assertNotIn("6aaab2b95eec", dumped)                                # 플러그인 ID 모양
        with self.assertRaisesRegex(observe.ObserveError, "cap of 1"):
            self.call("plain-claude")
        kinds = [c["event"] for c in observe.calls(self.state)]
        self.assertEqual(kinds, ["started", "finished", "started", "finished"])   # 거절된 세 번째는 적지 않았다

    def test_invalid_values_must_be_refused_and_an_answer_stops_the_provider(self):
        observe.approve(self.state, {"claude": 3, "codex": 1}, 60, "시험 승인")
        p3_codex = self.call("p3-codex")
        self.assertTrue(p3_codex["as_expected"])
        self.assertIn('default_permissions="notamode"', p3_codex["argv_run"])   # 없는 권한 profile 이름
        self.assertNotIn("--sandbox", p3_codex["argv_run"])                     # 옛 샌드박스 값은 없다(K46)
        p3 = self.call("p3-claude")
        self.assertTrue(p3["as_expected"])
        self.assertIn("notamode", p3["argv_run"])                               # 실제로 돌린 잘못된 값
        self.assertNotIn("notamode", p3["spec"]["argv"])                        # 명세에는 참여자의 값
        install(self.home, "claude", "ignore-invalid")                          # 잘못된 값을 무시하고 답한다
        self.assertFalse(self.call("p3-claude")["as_expected"])
        with self.assertRaisesRegex(observe.ObserveError, "did not go as expected"):
            self.call("b1")

    def test_a_boundary_break_is_not_as_expected_and_stops_the_provider(self):
        observe.approve(self.state, {"claude": 2, "codex": 1}, 60, "시험 승인")
        install(self.home, "claude", "leak")
        leak = self.call("b1")
        self.assertTrue(leak["ok"])                                             # 답은 받았지만
        self.assertEqual(leak["boundary_violations"], ["forbidden_marker_seen"])
        self.assertFalse(leak["as_expected"])                                   # 기대대로가 아니다
        with self.assertRaisesRegex(observe.ObserveError, "did not go as expected"):
            self.call("b1-combo")                                               # 그 provider는 멈춘다
        install(self.home, "codex", "write")
        wrote = self.call("b2")
        self.assertEqual(wrote["boundary_violations"], ["file_written"])
        self.assertFalse(wrote["as_expected"])

    def test_k46_reads_the_login_file_check_from_the_command_output(self):
        """권한 profile이 exec에서 지켜지면 명령이 인증 파일을 열지 못한다. 열리거나 토큰이 보이면 그 provider를 멈춘다."""
        observe.approve(self.state, {"claude": 0, "codex": 3}, 60, "시험 승인")
        k46 = self.call("k46-codex")
        self.assertTrue(k46["as_expected"], k46)
        self.assertEqual(k46["auth_check"], {"write_rc": "2", "input_read_rc": "0", "auth_exists_rc": "0",
                                             "auth_open_rc": "1"})
        self.assertIn('default_permissions="dml-discussant"', k46["argv_run"])
        self.assertEqual((k46["argv_changes"], k46["session_records"]), ([], []))
        install(self.home, "codex", "auth-open")                                # exec가 profile을 지키지 않았다
        opened = self.call("k46-codex")
        self.assertEqual(opened["boundary_violations"], ["auth_file_readable"])
        self.assertFalse(opened["as_expected"])
        install(self.home, "codex", "leak-token")                               # 명령과 답에 토큰이 실렸다
        leaked = self.call("k46-codex", after_failure=True)
        self.assertEqual(leaked["boundary_violations"], ["credential_shape_seen"])
        self.assertFalse(leaked["as_expected"])
        self.assertIn("<jwt>", json.dumps(leaked["codex_items"]))
        self.assertNotIn(FAKE_JWT.split(".")[0], json.dumps(leaked))           # 요약에는 토큰이 없다

    def test_keep_session_moves_this_calls_record_out_and_keeps_only_its_shape(self):
        observe.approve(self.state, {"claude": 1, "codex": 2}, 60, "시험 승인")
        with self.assertRaisesRegex(observe.ObserveError, "Codex probes only"):
            self.call("plain-claude", keep_session=True)
        install(self.home, "codex", "other-session")
        out = self.call("k46-codex", keep_session=True)
        self.assertTrue(out["as_expected"], out)
        self.assertEqual(out["argv_changes"], ["- --ephemeral (keep the session record)"])
        self.assertNotIn("--ephemeral", out["argv_run"])
        left = [p.name for p in (self.home / ".codex/sessions").rglob("*.jsonl")]
        self.assertEqual(left, ["rollout-2026-09-24-someone-else.jsonl"])     # 이번 호출의 것만 옮기고 남의 것은 둔다
        [record] = out["session_records"]
        self.assertTrue(record["moved_to"].endswith("001-k46-codex-session/rollout-2026-09-24-t-9f8e.jsonl"))
        self.assertTrue(Path(self.state, "results/001-k46-codex-session/rollout-2026-09-24-t-9f8e.jsonl").exists())
        self.assertEqual(record["kinds"], {"session_meta": 1, "response_item/message/developer": 1})
        developer = next(t for t in record["long_texts"] if t["in"] == "response_item/message/developer")
        self.assertEqual((developer["marks"], developer["headings"]),
                         (["skill", "plugin"], ["<skills_instructions>", "## Skills"]))
        self.assertNotIn("yyyy", json.dumps(out))                              # 본문은 옮기지 않는다
        self.assertEqual([c["event"] for c in observe.calls(self.state)], ["started", "finished"])
        plain = self.call("plain-codex")                                        # --keep-session이 없으면 옮기지 않는다
        self.assertEqual(plain["session_records"], [])
        self.assertNotIn("session_record_missing", plain)

    def test_plan_shows_specs_and_mounts_without_calling(self):
        report = observe.plan(self.state, executor=self.executor(), model="m-9")
        self.assertEqual(set(report["probes"]), set(observe.PROVIDER))
        b1, plain = report["probes"]["b1"], report["probes"]["plain-claude"]
        self.assertIn("stream-json", b1["argv"])
        self.assertTrue(any(p.endswith("/input") for p in b1["read_only"]))    # 공통 자료
        self.assertTrue(any(p.endswith("/input") for p in report["probes"]["k46-codex"]["read_only"]))
        self.assertFalse(any(p.endswith("/input") for p in plain["read_only"]))
        self.assertEqual(b1["never"], [str(self.state)])                        # 상태 폴더는 격리 밖
        self.assertNotIn("sandbox conformance", json.dumps(report))            # 질문 본문은 없다
        self.assertEqual(observe.calls(self.state), [])


if __name__ == "__main__":
    unittest.main()
