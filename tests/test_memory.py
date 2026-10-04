"""Task recall integration: visibility, frozen input, corruption and bounded recall.

Synthetic executors only. These do not establish retrieval or model quality.
"""
import hashlib
import json

from app import controller as c, fake_cli, memory
from app.store import Store
import test_app_controller as support
from test_general_team import Recording, ROSTER, board
from test_refine_mode import Refiner, board as refine_board
from test_collate import Collator
from test_split_proposal import Splitter
from test_next_step import Proposer, board as next_board
from test_model_synthesis import SynthExecutor


class MemoryTests(support.Base):
    def general(self, ctl, *, task_id=None, question="검색 도입 판단", **kwargs):
        return ctl.create_run(question, [ROSTER["claude"]], min_independent=1,
                              role_board=board("claude"), roster=ROSTER, task_id=task_id,
                              assignments={"claude": {"task": "검색 위험을 정리", "sources": []}}, **kwargs)

    def history(self, ctl, memo="기억 표식 MEMORY-ALPHA: 비용은 미확인"):
        rid = self.general(ctl)
        self.assertTrue(ctl.wait_idle())
        view = ctl.view(rid)["runs"][0]
        ctl.mark_reviewed(rid, view["result_revision"], memo=memo)
        return rid, self.store.row("SELECT task_id FROM runs WHERE run_id = ?", rid)["task_id"]

    def test_general_gets_memory_isolated_and_other_task_do_not(self):
        ex = Recording()
        ctl = self.controller(ex)
        prior, task = self.history(ctl)
        rid = self.general(ctl, task_id=task)
        self.assertTrue(ctl.wait_idle())
        self.assertIn("MEMORY-ALPHA", ex.prompts["claude"])
        pack = json.loads(self.store.row("SELECT role_config FROM runs WHERE run_id = ?", rid)["role_config"])["memory"]
        self.assertEqual(pack["entries"][0]["run_id"], prior)
        self.assertIn("실행 종류 synthetic", pack["entries"][0]["excerpt"])
        isolated = ctl.prepare_run("독립 비교", [ROSTER["codex"]], min_independent=1, task_id=task)
        self.assertTrue(isolated["role_config"]["memory"]["entries"])
        self.assertNotIn("MEMORY-ALPHA", isolated["prompt"])
        self.general(ctl)
        self.assertTrue(ctl.wait_idle())
        self.assertNotIn("MEMORY-ALPHA", ex.prompts["claude"])
        self.general(ctl, task_id=task, use_memory=False)
        self.assertTrue(ctl.wait_idle())
        self.assertNotIn("MEMORY-ALPHA", ex.prompts["claude"])

    def test_never_reads_sealed_failed_or_cancelled_runs(self):
        ctl = self.controller(Recording())
        prior, task = self.history(ctl)
        for phase, cancelled in [("drafting", 0), ("collected", 1), ("unknown", 0)]:
            with self.store.tx() as tx:
                tx.execute("UPDATE runs SET phase = ?, cancel_requested = ? WHERE run_id = ?", phase, cancelled, prior)
            self.assertEqual(memory.select(self.store, task, "검색")["entries"], [])

    def test_fixed_input_survives_history_changes_and_rejects_pack_tampering(self):
        ctl = self.controller(Recording())
        prior, task = self.history(ctl)
        ctl.max_parallel = 0
        rid = self.general(ctl, task_id=task)
        before = ctl._attempt_input(rid, "claude")[0]
        with self.store.tx() as tx:
            tx.execute("UPDATE drafts SET text = 'changed' WHERE run_id = ?", prior)
            tx.event(prior, "human_reviewed", revision=999, memo="새 메모")
        self.assertEqual(ctl._attempt_input(rid, "claude")[0], before)
        roles = json.loads(self.store.row("SELECT role_config FROM runs WHERE run_id = ?", rid)["role_config"])
        roles["memory"]["entries"][0]["excerpt"] = "tampered"
        with self.store.tx() as tx:
            tx.execute("UPDATE runs SET role_config = ? WHERE run_id = ?", json.dumps(roles), rid)
        with self.assertRaises(c.ControllerError):
            ctl._attempt_input(rid, "claude")

    def test_preview_changes_require_confirmation_again(self):
        ctl = self.controller(Recording())
        prior, task = self.history(ctl)
        args = dict(min_independent=1, task_id=task, role_board=board("claude"), roster=ROSTER,
                    assignments={"claude": {"task": "비교", "sources": []}})
        preview = ctl.prepare_run("검색", [ROSTER["claude"]], **args)
        with self.store.tx() as tx:
            tx.event(prior, "human_reviewed", revision=999, memo="새 근거")
        with self.assertRaisesRegex(c.ControllerError, "다시 확인"):
            ctl.create_run("검색", [ROSTER["claude"]], run_id=preview["run_id"],
                           confirmation=preview["confirmation"], **args)

    def test_ranking_bounds_unicode_escaping_and_source_digest(self):
        ctl = self.controller(Recording())
        prior, task = self.history(ctl)
        for q in ["검색 위험", "전혀 다른 주제", "새로운 주제", "더 새로운 주제"]:
            self.general(ctl, task_id=task, question=q)
            self.assertTrue(ctl.wait_idle())
        pack = memory.select(self.store, task, "검색 위험")
        self.assertEqual(len(pack["entries"]), memory.MAX_RUNS)
        self.assertIn("검색 위험", pack["entries"][0]["excerpt"])
        with self.store.tx() as tx:
            text = '한글😀"\\\n' * 2000
            tx.execute("UPDATE drafts SET text = ?, sha256 = ? WHERE run_id = ?", text,
                       hashlib.sha256(text.encode()).hexdigest(), prior)
        pack = memory.select(self.store, task, "검색 도입 판단")
        self.assertLessEqual(len(memory.footer(pack).encode()), memory.MAX_BYTES)
        self.assertTrue(next(e for e in pack["entries"] if e["run_id"] == prior)["truncated"])
        with self.store.tx() as tx:
            tx.execute("UPDATE drafts SET sha256 = 'bad' WHERE run_id = ?", prior)
        entry = next(e for e in memory.select(self.store, task, "검색 도입 판단")["entries"] if e["run_id"] == prior)
        self.assertNotIn("답변 claude", entry["excerpt"])

    def test_refiner_reuses_first_snapshot_and_cannot_move_memory_to_another_task(self):
        ctl = self.controller(Refiner())
        prior, task = self.history(ctl)
        key = ctl.refine(ROSTER["claude"], "검색할까", task_id=task)
        self.assertTrue(ctl.wait_idle())
        self.assertIn("MEMORY-ALPHA", self.store.row(
            "SELECT prompt FROM refine_turns WHERE refine_id = ?", key)["prompt"])
        with self.store.tx() as tx:
            tx.event(prior, "human_reviewed", revision=999, memo="CHANGED-LATER")
        ctl.refine(ROSTER["claude"], refine_id=key, note="비용도")
        self.assertTrue(ctl.wait_idle())
        text = self.store.row("SELECT prompt FROM refine_turns WHERE refine_id = ? AND turn = 2", key)["prompt"]
        self.assertIn("MEMORY-ALPHA", text)
        self.assertNotIn("CHANGED-LATER", text)
        with self.assertRaisesRegex(c.ControllerError, "새로 다듬"):
            ctl.prepare_run("다듬은 질문 2", [ROSTER["codex"]], min_independent=1,
                            role_board=refine_board("codex"), roster=ROSTER, refinement={"id": key, "turn": 2})

    def test_split_and_collation_receive_task_memory(self):
        ctl = self.controller(Splitter())
        _, task = self.history(ctl)
        key = ctl.propose_split("검색 도입 판단", ROSTER["claude"], [ROSTER["codex"]], task_id=task)
        self.assertTrue(ctl.wait_idle())
        self.assertIn("MEMORY-ALPHA", self.store.row("SELECT prompt FROM splits WHERE split_id = ?", key)["prompt"])
        # The run freezes history once; collation uses that exact snapshot.
        ctl.executor = Collator()
        rid = ctl.create_run("검색", [ROSTER["claude"]], min_independent=1, task_id=task,
                             role_board=board("claude", orchestrator=("claude",)), roster=ROSTER,
                             assignments={"claude": {"task": "위험", "sources": []}})
        self.assertTrue(ctl.wait_idle())
        key = ctl.collate(rid)
        self.assertTrue(ctl.wait_idle())
        self.assertIn("MEMORY-ALPHA", self.store.row(
            "SELECT prompt FROM collations WHERE collation_id = ?", key)["prompt"])

    def test_invalid_flag_rejected_before_start(self):
        ctl = self.controller(Recording())
        for value in ["false", 1, None]:
            with self.assertRaises(c.ControllerError):
                self.general(ctl, use_memory=value)
        self.assertFalse(ctl.executor.started)

    def test_mock_answer_echoes_current_goal_instead_of_history(self):
        for prompt in [c.GENERAL_PROMPT.format(question="현재 목표", task="현재 일"),
                       c.PROMPT.format(question="현재 목표")]:
            answer = fake_cli.answer("claude", prompt + '\n이전 질문: 과거 질문\n')
            self.assertIn("받은 질문: 현재 목표\n", answer)
            self.assertNotIn("받은 질문: 과거 질문", answer)

    def test_restart_resumes_the_frozen_general_input(self):
        ctl = self.controller(Recording())
        _, task = self.history(ctl)
        ctl.max_parallel = 0
        rid = self.general(ctl, task_id=task)
        expected = ctl._attempt_input(rid, "claude")[0]
        ctl.shutdown()
        self.store.close()
        self.store = Store(self.tmp / "store" / "journal.db")
        self.addCleanup(self.store.close)
        ex = Recording()
        resumed = self.controller(ex)
        resumed.resume()
        self.assertTrue(resumed.wait_idle())
        self.assertEqual(ex.prompts["claude"], expected)

    def test_next_step_memory_does_not_enter_isolated_draft(self):
        ex = Proposer()
        ctl = self.controller(ex)
        _, task = self.history(ctl)
        rid = ctl.create_run("비교", [ROSTER["codex"]], min_independent=1, task_id=task,
                             role_board=next_board("codex"), roster=ROSTER)
        self.assertTrue(ctl.wait_idle())
        self.assertNotIn("MEMORY-ALPHA", ex.prompts["codex"][-1])
        key = ctl.propose_next(rid)
        self.assertTrue(ctl.wait_idle())
        self.assertIn("MEMORY-ALPHA", self.store.row(
            "SELECT prompt FROM proposals WHERE proposal_id = ?", key)["prompt"])

    def test_synthesis_gets_memory_but_quotes_still_use_current_drafts(self):
        ctl = self.controller(Recording(), max_real_calls=3)
        _, task = self.history(ctl)
        ex = SynthExecutor()
        ctl.executor = ex
        rid = ctl.create_run("비교", [support.cli("claude"), support.cli("codex")], min_independent=2,
                             quorum_policy=c.INCLUDE_UNVERIFIED, task_id=task)
        self.assertTrue(ctl.wait_idle())
        ctl.synthesize_with_model(rid, "claude-code")
        self.assertTrue(support.wait_for(lambda: rid not in ctl._synthesis))
        self.assertIn("MEMORY-ALPHA", ex.prompts["synthesis"])
        self.assertNotIn("MEMORY-ALPHA", ex.prompts["codex"])
        self.assertEqual(ctl.call_budget(), {"used": 3, "cap": 3})
        self.assertEqual(self.run_view(ctl, rid)["synthesis"]["checks"]["exact_matches"], 4)
