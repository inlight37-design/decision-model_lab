"""판단 완료·작업 상태·합성 저장(카드 #109, 리뷰 통합 S2). 카드의 표를 그대로 시험한다.

- AH-01: '판단 완료'는 그때의 결과 판(공개·합성 완료·합성 실패 사건의 마지막 seq)에 묶인다. 새 합성이 끝나면
  다시 내 차례이고, 오래된 화면이 보낸 판은 거절하며, 같은 판은 사건 하나다. 재현 `human_review_after_new_synthesis`
  에서는 새 합성 뒤에도 '끝남'이었다.
- N3: 스스로 진행하는 것으로 확인된 상태만 '작업 중'이다. 재시작 뒤 멈춘 대기 시도와 표에 없는 상태는 사람 몫이다.
- AH-04: 합성 메타데이터의 고립 surrogate는 초안과 같은 규칙으로 저장한다. 재현 `synthesis_surrogate_metadata`에서는
  저장이 실패해 unknown·자리 1개로 남았다.

모델·프로세스는 쓰지 않는다. 실제처럼 분류되는 합성 실행기만 쓴다.
"""
import json
from unittest import mock

from app import controller as c
from app.roles import task_projection
from app.store import _Tx, events
from core import adapters, runner
import test_app_controller as support
import test_model_synthesis as synthesis
from test_synthesis_lifecycle import Unconfirmed


class ReviewBase(support.Base):
    def revealed(self, ex, cap=4):
        return synthesis.ControllerTests.revealed(self, ex, cap=cap)

    def synthesize(self, ctl, rid):
        ctl.synthesize_with_model(rid, "claude-code")
        self.assertTrue(support.wait_for(lambda: rid not in ctl._synthesis))

    def revision(self, ctl, rid):
        return self.run_view(ctl, rid)["result_revision"]

    def timeline(self, ctl, rid):
        return next(r for t in ctl.view()["tasks"] for r in t["runs"] if r["run_id"] == rid)

    def reviews(self, rid):
        return [e for e in events(self.store, rid) if e["kind"] == "human_reviewed"]


class ReviewRevisionTests(ReviewBase):
    def test_a_new_synthesis_reopens_my_turn_and_can_be_reviewed_again(self):
        ctl, rid = self.revealed(synthesis.SynthExecutor())
        self.synthesize(ctl, rid)
        first = self.revision(ctl, rid)
        ctl.mark_reviewed(rid, first)
        self.assertTrue(self.run_view(ctl, rid)["reviewed"])
        self.assertEqual(self.timeline(ctl, rid)["status"], "done")
        self.synthesize(ctl, rid)                                        # 합성2 — 아무도 아직 보지 않았다
        second = self.revision(ctl, rid)
        self.assertGreater(second, first)
        self.assertFalse(self.run_view(ctl, rid)["reviewed"])
        self.assertEqual((self.timeline(ctl, rid)["status"], self.timeline(ctl, rid)["action"]),
                         ("my_turn", "공개된 답 판단"))
        ctl.mark_reviewed(rid, second)                                   # 다시 판단할 수 있다 — 새 사건
        self.assertEqual(self.timeline(ctl, rid)["status"], "done")
        self.assertEqual([e["revision"] for e in self.reviews(rid)], [first, second])

    def test_a_stale_screen_cannot_review_a_newer_result(self):
        ctl, rid = self.revealed(synthesis.SynthExecutor())
        self.synthesize(ctl, rid)
        seen = self.revision(ctl, rid)                                   # 화면은 합성1을 보고 있다
        self.synthesize(ctl, rid)                                        # 그 사이 합성2가 끝났다
        with self.assertRaises(c.ControllerError):
            ctl.mark_reviewed(rid, seen)
        self.assertEqual(self.reviews(rid), [])
        self.assertFalse(self.run_view(ctl, rid)["reviewed"])

    def test_the_same_revision_twice_is_one_event_and_bad_revisions_are_refused(self):
        ctl, rid = self.revealed(synthesis.SynthExecutor())
        revision = self.revision(ctl, rid)                               # 합성 없이 공개된 초안만
        ctl.mark_reviewed(rid, revision)
        ctl.mark_reviewed(rid, revision)
        self.assertEqual(len(self.reviews(rid)), 1)
        for bad in (None, str(revision), True, float(revision)):
            with self.subTest(bad=bad), self.assertRaises(c.ControllerError):
                ctl.mark_reviewed(rid, bad)

    def test_a_confirmed_failed_synthesis_is_a_problem_until_reviewed_and_stays_failed(self):
        ctl, rid = self.revealed(synthesis.SynthExecutor(answer=lambda: "합성 형식이 아닌 답"))
        self.synthesize(ctl, rid)
        self.assertEqual(self.run_view(ctl, rid)["model_synthesis"]["status"], "failed")
        self.assertEqual((self.timeline(ctl, rid)["status"], self.timeline(ctl, rid)["action"]),
                         ("problem", "종료·실패 확인"))
        ctl.mark_reviewed(rid, self.revision(ctl, rid))
        # 사람이 그 판을 판단했다 — 작업은 끝남이지만 실패 기록은 그대로다. 품질 통과로 바꾸지 않는다.
        self.assertEqual(self.timeline(ctl, rid)["status"], "done")
        self.assertEqual(self.run_view(ctl, rid)["model_synthesis"]["status"], "failed")
        kinds = [e["kind"] for e in events(self.store, rid)]
        self.assertIn("synthesis_failed", kinds)
        self.assertNotIn("synthesis_completed", kinds)

    def test_an_earlier_unknown_synthesis_keeps_its_duty_and_slot_after_a_good_result(self):
        ctl, rid = self.revealed(Unconfirmed())
        self.synthesize(ctl, rid)                                        # 자손 전체의 종료를 확인하지 못했다
        ctl.synthesize(rid)                                              # 그 뒤 원문 대조표는 잘 나왔다
        view = self.run_view(ctl, rid)
        self.assertEqual(view["synthesis"]["status"], "completed")
        self.assertEqual(view["model_synthesis"]["status"], "unknown")
        self.assertEqual(ctl.view()["slots"]["used"], 1)
        self.assertEqual(self.timeline(ctl, rid)["status"], "problem")
        with self.assertRaises(c.ControllerError):
            ctl.mark_reviewed(rid, self.revision(ctl, rid))


class PausedTaskTests(support.Base):
    def test_queued_attempts_held_after_restart_are_my_turn_not_working(self):
        first = self.controller(support.SyntheticExecutor(), max_parallel=0)
        rid = first.create_run("질문", [support.cli("a")], min_independent=1)
        self.assertTrue(first.shutdown())
        ex = support.SyntheticExecutor()
        again = self.controller(ex)                                      # 같은 원장으로 다시 시작 — 멈춰 둔다
        self.assertTrue(again.paused)
        run = again.view()["tasks"][0]["runs"][0]
        self.assertEqual((run["status"], run["action"]), ("my_turn", "멈춘 시도 이어서 시작"))
        again.resume()
        self.assertTrue(again.wait_idle())
        self.assertEqual(ex.started, ["a"])
        self.assertEqual(again.view()["tasks"][0]["runs"][0]["status"], "my_turn")   # 공개됐고 판단할 차례


def projected(held=None, **run):
    """task_projection에 넣을 공개 투영 한 실행. 표의 각 줄은 필요한 칸만 바꾼다."""
    base = {"run_id": "r1", "task_id": "t1", "question": "q", "created_at": 1.0, "role_config": {},
            "participants": [{"state": "accepted"}], "cancel_requested": False, "reviewed": False,
            "gate": {"status": "waiting", "can_submit": True, "can_approve_reduction": False, "revealed": False},
            "model_synthesis": None, "model_syntheses": [], "budget": {"used": 1, "reserved": 0}}
    gate = {**base["gate"], **run.pop("gate", {})}
    tasks = [{"task_id": "t1", "title": "작업", "created_at": 1.0}]
    item = task_projection(tasks, [{**base, **run, "gate": gate}], held=held)[0]["runs"][0]
    return item["status"], item["action"]


class TaskProjectionTableTests(support.unittest.TestCase):
    def test_the_status_table(self):
        revealed = {"status": "revealed", "can_submit": False, "revealed": True}
        rows = [
            ("대기 중·멈춤", dict(held="paused", participants=[{"state": "queued"}]),
             ("my_turn", "멈춘 시도 이어서 시작")),
            ("대기 중·종료 미확인 상한", dict(held="unsettled", participants=[{"state": "queued"}]),
             ("problem", "종료 미확인 정리 뒤 시작")),
            ("대기 중·스스로 시작됨", dict(participants=[{"state": "queued"}]), ("working", None)),
            ("실행 중", dict(held="paused", participants=[{"state": "running"}]), ("working", None)),
            ("표에 없는 상태(모두 끝났는데 공개 전)", dict(gate={"status": "ready", "can_submit": True}),
             ("problem", "상태 확인")),
            ("수동 답 대기가 멈춤보다 앞선다", dict(held="paused", participants=[{"state": "awaiting_user"},
                                                                            {"state": "queued"}]),
             ("my_turn", "원본 앱 답 붙여넣기")),
            ("축소 승인", dict(gate={"status": "reduction_required", "can_approve_reduction": True},
                             participants=[{"state": "accepted"}, {"state": "rejected"}]),
             ("my_turn", "축소 여부 판단")),
            ("종료 미확인 참여자", dict(participants=[{"state": "unknown"}, {"state": "queued"}]),
             ("problem", "종료·실패 확인")),
            ("종료 미확인 합성은 판단 완료여도", dict(gate=revealed, reviewed=True, model_synthesis={"status": "unknown"}),
             ("problem", "종료·실패 확인")),
            ("확인된 합성 실패·판단 전", dict(gate=revealed, model_synthesis={"status": "failed"}),
             ("problem", "종료·실패 확인")),
            ("확인된 합성 실패·판단 뒤", dict(gate=revealed, reviewed=True, model_synthesis={"status": "failed"}),
             ("done", None)),
            ("합성 중", dict(gate=revealed, model_synthesis={"status": "running"}), ("working", None)),
            ("공개·판단 전", dict(gate=revealed), ("my_turn", "공개된 답 판단")),
            ("공개·판단 뒤", dict(gate=revealed, reviewed=True), ("done", None)),
            ("취소 요청", dict(cancel_requested=True, gate={"status": "cancelled", "can_submit": False}),
             ("problem", "실행 확인")),
        ]
        for name, run, expected in rows:
            with self.subTest(name):
                self.assertEqual(projected(**run), expected)


class SynthesisMetadataTests(ReviewBase):
    class Surrogate(synthesis.SynthExecutor):
        """합성자의 보고 모델 목록에 고립 surrogate가 섞인다. 요청한 모델도 있어 model_match는 참이다."""

        def execute(self, spec, prompt, work_dir, timeout, *, cancel=None):
            result, outcome = super().execute(spec, prompt, work_dir, timeout, cancel=cancel)
            if spec.pid != "synthesis":
                return result, outcome
            body = json.loads(result.stdout)
            body["modelUsage"]["\ud800"] = {}
            result = runner.RunResult(result.argv, result.state, result.exit_code, json.dumps(body), "", False, False,
                                      5, 0, True, containment=runner.JOB_OBJECT, input_delivery=runner.INPUT_COMPLETE)
            return result, adapters.interpret("claude-code", result, requested_model="m")

    def test_surrogate_metadata_is_escaped_and_stored_like_drafts(self):
        ctl, rid = self.revealed(self.Surrogate())
        self.synthesize(ctl, rid)
        view = self.run_view(ctl, rid)
        self.assertEqual(view["model_synthesis"]["status"], "completed")
        self.assertIs(view["synthesis"]["escaped_text"], True)
        self.assertIn("\\ud800", view["synthesis"]["synthesizer"]["reported_models"])
        self.assertEqual(ctl.view()["slots"]["used"], 0)
        self.assertEqual(ctl.unsettled(), 0)

    def test_a_real_ledger_write_failure_still_leaves_the_synthesis_unknown(self):
        ctl, rid = self.revealed(synthesis.SynthExecutor())
        real = _Tx.event

        def failing(tx, run_id, kind, **payload):
            if kind == "synthesis_completed":
                raise OSError("disk full (test)")
            return real(tx, run_id, kind, **payload)

        with mock.patch.object(_Tx, "event", failing):
            self.synthesize(ctl, rid)
        self.assertEqual(self.run_view(ctl, rid)["model_synthesis"]["status"], "unknown")
        self.assertEqual(ctl.view()["slots"]["used"], 1)                 # 자리를 쥔다
        self.assertIn("synthesis_result_not_stored", [e["kind"] for e in events(self.store, rid)])


if __name__ == "__main__":
    support.unittest.main()
