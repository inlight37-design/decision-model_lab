"""K42: 인증 전 연결 상한과 slow-trickle I/O 기한. CPU/모델 자원 제한 시험은 아니다."""
from http.server import BaseHTTPRequestHandler
import socket
import threading
import time
import unittest
from unittest.mock import patch

from app.server import _Server


class ConnectionLimitTests(unittest.TestCase):
    def server(self, handler, *, capacity=1, deadline=0.3):
        with patch.object(_Server, "max_connections", capacity):
            server = _Server(("127.0.0.1", 0), handler)
        server.connection_deadline = deadline
        loop = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        loop.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def connect(self, server):
        sock = socket.create_connection(server.server_address, timeout=2)
        self.addCleanup(sock.close)
        return sock

    def test_saturation_does_not_start_another_handler_and_capacity_is_reused(self):
        entered, release = threading.Event(), threading.Event()
        seen = []
        class Handler(BaseHTTPRequestHandler):
            def handle(self):
                seen.append(1)
                entered.set()
                release.wait(2)
        server = self.server(Handler, deadline=2)
        self.addCleanup(release.set)
        first = self.connect(server)
        self.assertTrue(entered.wait(1))
        second = self.connect(server)
        self.assertEqual(second.recv(1), b"")
        self.assertEqual(len(seen), 1)
        release.set()
        first.recv(1)
        # 실제 종료의 마지막 finally까지 기다리고 슬롯을 즉시 반환한다.
        self.assertTrue(server._connections.acquire(timeout=1))
        server._connections.release()
        entered.clear()
        self.connect(server)
        self.assertTrue(entered.wait(1))
        self.assertEqual(len(seen), 2)

    def test_trickle_bytes_do_not_extend_absolute_connection_io_deadline(self):
        entered, ended = threading.Event(), threading.Event()
        class Handler(BaseHTTPRequestHandler):
            def handle(self):
                self.request.settimeout(1)  # 유휴 timeout보다 훨씬 자주 데이터를 보낸다.
                entered.set()
                try:
                    while self.request.recv(1):
                        pass
                except OSError:
                    pass
                finally:
                    ended.set()
        server = self.server(Handler)
        sock = self.connect(server)
        self.assertTrue(entered.wait(1))
        started = time.monotonic()
        while not ended.wait(0.02) and time.monotonic() - started < 1.5:
            try:
                sock.sendall(b"x")
            except OSError:
                break
        self.assertTrue(ended.wait(1))
        self.assertLess(time.monotonic() - started, 1.5)
        self.assertTrue(server._connections.acquire(timeout=1))
        server._connections.release()

    def test_thread_creation_failure_does_not_leak_connection_permit(self):
        server = _Server(("127.0.0.1", 0), BaseHTTPRequestHandler)
        self.addCleanup(server.server_close)
        sock = socket.socket()
        self.addCleanup(sock.close)
        with patch.object(threading.Thread, "start", side_effect=RuntimeError("no thread")):
            with self.assertRaises(RuntimeError):
                server.process_request(sock, ("127.0.0.1", 1))
        for _ in range(server.max_connections):
            self.assertTrue(server._connections.acquire(blocking=False))

    def test_deadline_thread_failure_closes_socket_and_releases_permit(self):
        server = _Server(("127.0.0.1", 0), BaseHTTPRequestHandler)
        self.addCleanup(server.server_close)
        request = socket.socket()
        self.addCleanup(request.close)
        self.assertTrue(server._connections.acquire(blocking=False))
        with patch.object(threading.Timer, "start", side_effect=RuntimeError("no timer")):
            with self.assertRaises(RuntimeError):
                server.process_request_thread(request, ("127.0.0.1", 1))
        self.assertEqual(request.fileno(), -1)
        for _ in range(server.max_connections):
            self.assertTrue(server._connections.acquire(blocking=False))
