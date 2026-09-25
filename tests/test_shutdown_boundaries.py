"""종료 대기의 입력 경계와 HTTP 스레드 시작 실패의 교차 회귀. 모델 호출 없음."""
from __future__ import annotations

import socket
from socketserver import BaseRequestHandler
import threading
import unittest
from unittest.mock import patch

from app.server import _Server
import test_app_controller as support


class IdleDeadlineTests(support.Base):
    def test_invalid_idle_deadline_is_rejected_even_when_already_idle(self):
        ctl = self.controller(support.SyntheticExecutor())
        for timeout in (-1, float("nan"), float("inf")):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                ctl.wait_idle(timeout)
        self.assertTrue(ctl.wait_idle(0))
        self.assertFalse(ctl.paused)


class HttpHandlerOwnershipTests(unittest.TestCase):
    def test_start_failure_reaps_only_unstarted_thread_and_keeps_live_handler(self):
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()

        class BlockingHandler(BaseRequestHandler):
            def handle(self):
                entered.set()
                release.wait(5)
                finished.set()

        server = _Server(("127.0.0.1", 0), BlockingHandler)
        first, first_peer = socket.socketpair()
        second, second_peer = socket.socketpair()
        try:
            server.process_request(first, ("127.0.0.1", 1))
            self.assertTrue(entered.wait(2))
            active = list(server._threads)
            self.assertEqual(len(active), 1)
            self.assertTrue(active[0].is_alive())
            with patch("threading.Thread.start", side_effect=RuntimeError("synthetic start failure")):
                with self.assertRaises(RuntimeError):
                    server.process_request(second, ("127.0.0.1", 2))
            # 미시작 스레드만 제거한다. 먼저 실행 중이던 writer는 join 목록에서 빠지면 안 된다.
            self.assertEqual(list(server._threads), active)
            self.assertFalse(finished.is_set())
            release.set()
            server.server_close()
            self.assertTrue(finished.is_set())
            self.assertFalse(active[0].is_alive())
        finally:
            release.set()
            server.server_close()
            for connection in (first, first_peer, second, second_peer):
                connection.close()


if __name__ == "__main__":
    unittest.main()
