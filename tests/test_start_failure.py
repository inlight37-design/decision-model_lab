"""실행 시작 실패와 정리(카드 #108, 리뷰 통합 S1). 구조 검토의 두 재현을 올바른 기대값으로 옮겼다.

- AH-03: 프로세스를 띄운 뒤 입출력 스레드를 시작하지 못해도 트리 종료·회수·닫기를 시도하고, 결과는 확인된
  종료(aborted) 또는 unknown이다. 재현 `R1-post-spawn-thread-failure`는 예외가 빠져나가고 kill·close가 0번이었다.
- AH-02: 참여자 작업 폴더를 준비하지 못하면 그 참여자만 시작 전 실패로 닫힌다. 재현 `filesystem_head_of_line`은
  두 실행이 모두 queued로 남고 create_run이 FileExistsError로 끝났다.

모델은 부르지 않는다. runner 시험은 이 테스트를 돌리는 python을 가짜 CLI로 쓰고, controller 시험은 프로세스 없는
합성 실행기만 쓴다.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from app import controller as c
from app.store import events
from core import adapters, runner
import test_app_controller as support
from test_live_cli import UnverifiedSynthetic
import test_model_synthesis as synthesis_support

CWD = tempfile.gettempdir()


class PostSpawnThreadFailureTests(unittest.TestCase):
    """AH-03. 스레드 시작 실패는 자원 부족에서 온다 — 여기서는 start()를 실패시켜 흉내 낸다."""

    def test_the_review_probe_now_cleans_up_instead_of_raising(self):
        # 구조 검토 core-probe.py의 R1 그대로: Popen·_Tree는 대역, 읽기 스레드 시작만 실패한다. 실제 자식은 없다.
        for confirmed, state in ((True, runner.ABORTED), (False, runner.UNKNOWN)):
            with self.subTest(confirmed=confirmed):
                proc = mock.Mock(pid=424242, stdout=mock.Mock(), stderr=mock.Mock(), stdin=None)
                proc.poll.return_value = -9
                tree = mock.Mock(note=None, containment=runner.JOB_OBJECT)
                tree.confirm_empty.return_value = confirmed
                reader = mock.Mock()
                reader.start.side_effect = RuntimeError("can't start new thread (synthetic)")
                with mock.patch.object(runner.subprocess, "Popen", return_value=proc) as popen, \
                        mock.patch.object(runner, "_Tree", return_value=tree), \
                        mock.patch.object(runner, "_Reader", return_value=reader):
                    result = runner._execute((str(Path(CWD) / "synthetic-cli"),), cwd=CWD, env={}, timeout=1,
                                             stdin_text=None, max_output_bytes=1024, cancel=None,
                                             pid_namespace=False)
                self.assertEqual((popen.call_count, tree.kill.call_count, tree.close.call_count), (1, 1, 1))
                self.assertEqual(result.state, state)                  # 확인된 종료 또는 unknown — 성공이 아니다
                reader.join.assert_not_called()                        # 시작하지 못한 스레드는 기다리지 않는다
                proc.stdout.close.assert_called_once()                 # 읽는 스레드가 없는 파이프는 닫는다
                proc.stderr.close.assert_called_once()
                self.assertTrue(any("could not start its I/O threads" in n for n in result.notes), result.notes)
                self.assertFalse(adapters.interpret("claude-code", result, requested_model="m").ok)

    def test_each_io_thread_that_cannot_start_ends_the_real_process(self):
        """읽기(stdout)·읽기(stderr)·쓰기(stdin) 스레드가 각각 시작하지 못하는 세 경우. 실제 자식은 30초 잔다."""
        for failing, name in ((1, "stdout reader"), (2, "stderr reader"), (3, "stdin writer")):
            with self.subTest(name):
                calls, spawned = [], []
                real_start, real_popen = threading.Thread.start, subprocess.Popen

                def start(thread, failing=failing, calls=calls):
                    calls.append(thread)
                    if len(calls) == failing:
                        raise RuntimeError("can't start new thread (test)")
                    real_start(thread)

                def popen(*args, spawned=spawned, **kwargs):
                    spawned.append(real_popen(*args, **kwargs))
                    return spawned[-1]

                with mock.patch.object(runner._Reader, "start", start), \
                        mock.patch.object(runner._Writer, "start", start), \
                        mock.patch.object(runner.subprocess, "Popen", popen):
                    began = time.monotonic()
                    result = runner.run([sys.executable, "-c", "import sys, time; sys.stdin.read(); time.sleep(30)"],
                                        cwd=CWD, env=dict(os.environ), timeout=20, stdin_text="질문")
                    took = time.monotonic() - began
                self.assertEqual(result.state, runner.ABORTED, result.notes)
                self.assertIs(result.unit_confirmed_empty, True)
                self.assertIsNotNone(spawned[0].poll())                # 회수까지 했다
                self.assertLess(took, runner.CLEANUP_LIMIT)            # 정리 대기의 상한 안에서 돌아온다
                outcome = adapters.interpret("claude-code", result, requested_model="m")
                self.assertEqual((outcome.ok, outcome.status), (False, "process_aborted"))
                if failing == 3:
                    self.assertEqual(result.input_delivery, runner.INPUT_FAILED)


class WorkFolderFailureTests(support.Base):
    """AH-02. 실제 호출처럼 예약하는 합성 실행기로 본다 — 예약이 없어야 호출이 없었다는 뜻이다."""

    def test_a_participant_whose_folder_cannot_be_made_does_not_block_the_queue(self):
        # 구조 검토 controller-probes.py의 filesystem_head_of_line: 첫 참여자 작업 폴더 자리에 일반 파일이 있다.
        ex = UnverifiedSynthetic()
        ctl = self.controller(ex, max_real_calls=4)
        options = {"min_independent": 1, "quorum_policy": c.INCLUDE_UNVERIFIED}
        preview = ctl.prepare_run("first", [support.cli("a"), support.cli("b")], **options)
        blocker = Path(ctl.work_root) / preview["run_id"] / "a"
        blocker.parent.mkdir(parents=True)
        blocker.write_text("ordinary existing file occupies participant work directory", encoding="utf-8")
        first = ctl.create_run("first", [support.cli("a"), support.cli("b")], run_id=preview["run_id"],
                               confirmation=preview["confirmation"], **options)
        second = ctl.create_run("second", [support.cli("c")], **options)
        self.assertTrue(ctl.wait_idle())
        a = self.part(ctl, first, "a")
        self.assertEqual((a["state"], a["status"]), (c.REJECTED, "process_failed_to_start"))   # view()가 보인다
        self.assertEqual(sorted(ex.started), ["b", "c"])                  # 같은 실행·다른 실행 모두 진행했다
        self.assertEqual(self.part(ctl, second, "c")["state"], c.ACCEPTED)
        reserved = sorted(e["pid"] for rid in (first, second)
                          for e in events(self.store, rid) if e["kind"] == "live_call_reserved")
        self.assertEqual(reserved, ["b", "c"])                            # 실패한 참여자는 예약하지 않았다
        refused = next(e for e in events(self.store, first) if e["kind"] == "attempt_started" and e["pid"] == "a")
        self.assertIn("FileExistsError", refused["spec"]["refused"])

    def test_a_synthesis_folder_that_cannot_be_made_is_a_refused_request(self):
        ex = synthesis_support.SynthExecutor()
        ctl, rid = synthesis_support.ControllerTests.revealed(self, ex, cap=3)
        run_dir = Path(ctl.work_root) / rid
        shutil.rmtree(run_dir)
        run_dir.write_text("ordinary file where the run folder was", encoding="utf-8")
        with self.assertRaises(c.ControllerError):                         # 파일 시스템 예외가 API 밖으로 새지 않는다
            ctl.synthesize_with_model(rid, "claude-code")
        self.assertEqual(ctl.call_budget(), {"used": 2, "cap": 3})
        self.assertNotIn("synthesis", ex.started)
        self.assertFalse([e for e in events(self.store, rid) if e["kind"] == "synthesis_started"])


if __name__ == "__main__":
    unittest.main()
