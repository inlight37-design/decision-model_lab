"""core.contract 검사 — 최종 계획의 판(지문)과 옛 이름 판의 대응(순서 5, G4). CLI·모델은 부르지 않는다."""
import os
import posixpath
import sys
import unittest
from unittest import mock

from core import adapters, contract, isolation

HOME = "/home/u"
EXE = {"claude-code": "/home/u/.local/share/claude/versions/2.1.280",
       "codex": "/home/u/.codex/packages/standalone/releases/0.156.1-x86_64-unknown-linux-musl/bin/codex"}


@mock.patch.object(adapters.os.path, "isabs", posixpath.isabs)
def participant_plan(adapter_id, *, inputs=(), home=HOME, exe=None, model="m", prompt="질문", variant=None):
    """app.cli_executor.CliExecutor.plan()과 같은 틀을 실제 CLI 없이 만든다(POSIX 경로)."""
    exe = exe or EXE[adapter_id].replace(HOME, home)
    if adapter_id == "claude-code":
        spec = adapters.build_spec(adapter_id, exe=exe, prompt=prompt, model=model, read_dirs=inputs)
        ro, rw = (exe,), (home + "/.claude", home + "/.claude.json")
    else:
        spec = adapters.build_spec(adapter_id, exe=exe, prompt=prompt, model=model, codex_user_home=home)
        ro, rw = (os.path.dirname(os.path.dirname(exe)),), (home + "/.codex",)
    if variant:
        spec = adapters.ExecutionSpec(spec.adapter_id, tuple(variant(list(spec.argv))), spec.stdin_text,
                                      spec.input_via, spec.input_sha256, spec.input_bytes)
    box = isolation.Sandbox(work_dir="/tmp/work", home=home, read_only=ro + tuple(inputs), read_write=rw)
    tmpl = contract.template(spec, box, home=home, inputs=inputs,
                             stderr_marks=adapters.STDERR_MARKS.get(adapter_id, ()))
    return contract.revision(tmpl), tmpl


def participant_revision(adapter_id, **kwargs):
    return participant_plan(adapter_id, **kwargs)[0]


class RevisionTests(unittest.TestCase):
    def test_values_that_change_every_attempt_do_not_change_the_revision(self):
        for adapter_id in EXE:
            with self.subTest(adapter=adapter_id):
                base = participant_revision(adapter_id, inputs=("/tmp/in",))
                self.assertEqual(base, participant_revision(adapter_id, inputs=("/srv/other",), home="/home/v",
                                                            model="other-model", prompt="다른 질문"))
                self.assertTrue(base.startswith(adapter_id + "@"))

    def test_what_changes_the_run_changes_the_revision(self):
        """자료 유무·출력 형식·세션 보존·연결은 실행 의미가 다르다. 관측 변형으로 본 관측이 참여자 계획을 뒷받침하지 않는다."""
        def legacy_json(argv):
            i = argv.index("--output-format")
            argv[i + 1] = "json"
            return [a for a in argv if a != "--verbose"]

        claude = participant_revision("claude-code")
        codex = participant_revision("codex", inputs=("/tmp/in",))
        others = {
            "claude with materials": participant_revision("claude-code", inputs=("/tmp/in",)),
            "claude legacy json": participant_revision("claude-code", variant=legacy_json),
            "codex without materials": participant_revision("codex"),
            "codex keeping the session": participant_revision(
                "codex", inputs=("/tmp/in",), variant=lambda a: [x for x in a if x != "--ephemeral"]),
        }
        for name, revision in others.items():
            with self.subTest(variant=name):
                self.assertNotIn(revision, (claude, codex))
        self.assertEqual(len(set(others.values())), len(others))

    def test_an_additional_codex_input_mount_changes_the_revision(self):
        one = participant_revision("codex", inputs=("/tmp/in",))
        two = participant_revision("codex", inputs=("/tmp/in", "/tmp/other"))
        self.assertNotEqual(one, two)
        self.assertTrue(contract.covers("discussant-2", one))
        self.assertFalse(contract.covers("discussant-2", two))

    def test_stdin_matching_an_option_does_not_hide_the_option(self):
        for adapter_id, prompt in (("codex", "--ephemeral"), ("codex", "-"),
                                   ("claude-code", "Read"), ("claude-code", "--restricted")):
            with self.subTest(adapter=adapter_id, prompt=prompt):
                baseline = participant_plan(adapter_id, inputs=("/tmp/in",))
                matching = participant_plan(adapter_id, inputs=("/tmp/in",), prompt=prompt)
                self.assertEqual(baseline, matching)

    def test_the_prompt_never_enters_the_record(self):
        spec = adapters.build_spec("claude-code", exe=sys.executable, prompt="비밀 질문", model="m")
        plan = contract.Plan(contract.REAL, spec, "/tmp/work", None, "m", revision="claude-code@x")
        self.assertNotIn("비밀 질문", repr(plan.record()))
        self.assertEqual(plan.record()["kind"], contract.REAL)


class LegacyTests(unittest.TestCase):
    def test_codex_discussant_2_covers_exactly_the_plan_k46_ran(self):
        """K46(2026-09-24): 참여자 argv 그대로(argv_changes 없음), 공통 자료 하나 읽기 전용. 자료 없는 계획은 대응하지 않는다."""
        k46 = participant_revision("codex", inputs=("/tmp/in",))
        self.assertEqual(contract.LEGACY["discussant-2"], (k46,))
        self.assertTrue(contract.covers("discussant-2", k46))
        self.assertFalse(contract.covers("discussant-2", participant_revision("codex")))

    def test_claude_discussant_1_covers_no_participant_plan(self):
        """2단계 b1은 stream-json·Read 도구·공통 자료로 관측했다. controller 계획 그대로 다시 관측한다."""
        for inputs in ((), ("/tmp/in",)):
            with self.subTest(inputs=inputs):
                self.assertFalse(contract.covers("discussant-1", participant_revision("claude-code", inputs=inputs)))

    def test_a_revision_covers_itself_and_nothing_is_covered_without_a_plan(self):
        revision = participant_revision("claude-code")
        self.assertTrue(contract.covers(revision, revision))
        for recorded, current in ((revision, None), (None, revision), ("", revision), (revision, "codex@0")):
            with self.subTest(recorded=recorded, current=current):
                self.assertFalse(contract.covers(recorded, current))


if __name__ == "__main__":
    unittest.main()
