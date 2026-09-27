"""바탕 화면 아이콘의 입구(app/launch.py·app/start.ps1). 모델·CLI·서버를 부르지 않는다.

launch.py가 스스로 정하는 세 가지(관측 기록·원장·끄기 요청)를 본다. 준비 조회·원장 상한·봉인은 app.server의 것이라
여기서 다시 시험하지 않는다. 실제 창을 열고 닫는 흐름은 2026-09-25 aux-pc에서 사람이 본 것이다(인계 1절).
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

from app import launch, registration
from app.store import Store
from registration_support import isolate

ROOT = Path(__file__).resolve().parents[1]


def ledger(folder: Path, caps: dict[str, int] | None, reserved: dict[str, int]) -> Path:
    """상한을 고정하고 예약 사건을 남긴 원장 하나(controller 없이 같은 표를 쓴다)."""
    folder.mkdir(parents=True)
    store = Store(folder / "journal.db")
    try:
        if caps is not None:
            store.bind_call_budget(sum(caps.values()), caps)
        with store.tx() as tx:
            for adapter, count in reserved.items():
                for _ in range(count):
                    tx.event("r1", "live_call_reserved", adapter_id=adapter, cap=sum((caps or {}).values()))
    finally:
        store.close()
    return folder


class LedgerChoiceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="dml-launch-")
        self.addCleanup(tmp.cleanup)
        self.live = Path(tmp.name) / "live"

    def test_the_newest_ledger_is_reused_while_every_provider_has_a_call_left(self):
        ledger(self.live / "20260925-100000", launch.CAPS, {"codex": 5, "claude-code": 5})
        newest = ledger(self.live / "20260925-120000", launch.CAPS, {"codex": 4, "claude-code": 2})
        self.assertEqual(launch.pick_ledger(self.live), newest)

    def test_a_provider_at_its_cap_opens_a_new_ledger_and_keeps_the_old_one(self):
        full = ledger(self.live / "20260925-120000", launch.CAPS, {"codex": 5, "claude-code": 1})
        chosen = launch.pick_ledger(self.live)
        self.assertNotEqual(chosen, full)
        self.assertFalse(chosen.exists())                 # 서버가 만든다
        self.assertTrue((full / "journal.db").is_file())  # 앞 원장은 지우지 않는다

    def test_a_ledger_fixed_with_other_caps_is_not_reused(self):
        other = ledger(self.live / "20260925-120000", {"codex": 1, "claude-code": 1}, {})
        self.assertNotEqual(launch.pick_ledger(self.live), other)

    def test_a_fresh_ledger_without_calls_is_reused(self):
        fresh = ledger(self.live / "20260925-120000", None, {})
        self.assertEqual(launch.pick_ledger(self.live), fresh)

    def test_no_ledger_yet_names_a_new_folder(self):
        chosen = launch.pick_ledger(self.live)
        self.assertEqual(chosen.parent, self.live)
        self.assertFalse(chosen.exists())


class ManifestChoiceTests(unittest.TestCase):
    def setUp(self):
        isolate(self)
        tmp = tempfile.TemporaryDirectory(prefix="dml-launch-root-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def record(self, folder: str, updated: str) -> Path:
        path = self.root / "docs" / "reviews" / folder / "manifest.v2.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"schema": "runtime-inventory/2", "host": {"label": "test-host"},
                                    "updated_at": updated, "adapters": []}), encoding="utf-8")
        return path

    def test_only_records_registered_on_this_machine_count_and_the_newest_wins(self):
        old = self.record("2026-09-01-a", "2026-09-01")
        new = self.record("2026-09-25-b", "2026-09-25")
        self.assertIsNone(launch.pick_manifest(self.root))
        registration.register(old, "test-host")
        self.assertEqual(launch.pick_manifest(self.root), old)
        registration.register(new, "test-host")
        self.assertEqual(launch.pick_manifest(self.root), new)


class StopTests(unittest.TestCase):
    def test_the_watch_stops_the_server_only_once_the_controller_is_idle(self):
        with tempfile.TemporaryDirectory() as tmp:
            stop_file = Path(tmp) / "stop-request"
            stop_file.touch()
            server, controller = mock.Mock(), mock.Mock()
            controller.wait_idle.side_effect = [False, False, True]   # 돌던 호출이 두 번 확인한 뒤 끝났다
            watcher = threading.Thread(target=launch._watch, args=(server, controller, stop_file, 0.01))
            watcher.start()
            watcher.join(5)
            self.assertFalse(watcher.is_alive())
            server.shutdown.assert_called_once_with()
            self.assertEqual(controller.wait_idle.call_count, 3)
            controller.wait_idle.assert_called_with(0)
            self.assertFalse(stop_file.exists())

    def test_the_watch_does_nothing_without_a_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, controller = mock.Mock(), mock.Mock()
            controller.wait_idle.return_value = True
            watcher = threading.Thread(target=launch._watch, args=(server, controller, Path(tmp) / "none", 0.01),
                                       daemon=True)
            watcher.start()
            time.sleep(0.1)
            server.shutdown.assert_not_called()


class UrlTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="dml-launch-state-")
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.dict(os.environ, {"DML_LAUNCHER_DIR": tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)

    def url(self, nonce: str) -> tuple[int, dict]:
        with mock.patch("builtins.print") as printed:
            code = launch.url(mock.Mock(wait=0, nonce=nonce))
        return code, json.loads(printed.call_args[0][0])

    def test_a_refusal_carries_its_reasons_and_exit_3(self):
        launch._write_state({"pid": 1, "mode": "live", "status": "refused", "nonce": "n1", "reasons": ["expired"]})
        code, out = self.url("n1")
        self.assertEqual((code, out["status"], out["reasons"]), (3, "refused", ["expired"]))

    def test_an_earlier_serve_state_is_not_taken_for_this_one(self):
        launch._write_state({"pid": 1, "mode": "live", "status": "stopped", "nonce": "old"})
        code, out = self.url("new")
        self.assertEqual((code, out["status"]), (1, "not_started"))

    def test_the_state_file_never_holds_the_token(self):
        launch._write_state({"pid": 1, "mode": "live", "status": "running", "port": 8765, "ledger": "/x"})
        self.assertNotIn("token", launch._paths()["state"].read_text(encoding="utf-8"))


class OwnerTests(unittest.TestCase):
    """카드 #120(S5, AH-07): 동시 시작의 패자가 살아 있는 서버의 기록을 덮지 못하고, 그 nonce의 url은 살아 있는 서버에
    합류하며, 끄기는 소유자에게만 닿는다. 실제 프로세스 경쟁 대신 함수·임시 폴더로 순서를 만든다."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="dml-launch-owner-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        patcher = mock.patch.dict(os.environ, {"DML_LAUNCHER_DIR": tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        owner = mock.patch.object(launch, "_OWNER", None)
        owner.start()
        self.addCleanup(owner.stop)

    def running(self, nonce="A", pid=4242):
        ledger_dir = self.root / "ledger"
        ledger_dir.mkdir(exist_ok=True)
        (ledger_dir / "control-token").write_text("TOKEN", encoding="utf-8")
        launch._write_state({"pid": pid, "mode": "mock", "status": "running", "port": 8766, "nonce": nonce,
                             "ledger": str(ledger_dir)})

    def call(self, fn, **kwargs):
        with mock.patch("builtins.print") as printed:
            code = fn(mock.Mock(**kwargs))
        return code, json.loads(printed.call_args[0][0])

    @unittest.skipUnless(hasattr(os, "fork") and os.name == "posix", "flock은 Linux의 launch에서만 쓴다")
    def test_the_loser_of_a_simultaneous_start_leaves_the_owners_record_alone(self):
        self.running("A")
        (self.root / "server.log").write_text("owner log", encoding="utf-8")
        (self.root / "stop-request").write_text("4242", encoding="utf-8")
        before = launch._paths()["state"].read_bytes()
        import fcntl
        holder = os.open(launch._paths()["lock"], os.O_RDWR | os.O_CREAT, 0o600)   # 첫 serve가 쥔 잠금
        self.addCleanup(os.close, holder)
        fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with mock.patch.object(launch, "_alive", return_value=False):   # 기록만으로는 살아 있는지 모르는 순간
            code, out = self.call(launch.serve, mock=True, nonce="B", avoid_ports="")
        self.assertEqual((code, out["reason"]), (1, "already running"))
        self.assertEqual(launch._paths()["state"].read_bytes(), before)            # 기록을 덮지 않았다
        self.assertEqual((self.root / "server.log").read_text(encoding="utf-8"), "owner log")   # 로그도
        self.assertEqual((self.root / "stop-request").read_text(encoding="utf-8"), "4242")      # 끄기 요청도
        self.assertTrue((self.root / "lost-B").exists())

    @unittest.skipUnless(hasattr(os, "fork") and os.name == "posix", "flock은 Linux의 launch에서만 쓴다")
    def test_only_one_holder_of_the_owner_lock(self):
        self.assertTrue(launch._acquire_owner())
        self.addCleanup(lambda: os.close(launch._OWNER))
        import fcntl
        other = os.open(launch._paths()["lock"], os.O_RDWR)
        self.addCleanup(os.close, other)
        with self.assertRaises(OSError):
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_the_losers_url_joins_the_live_server(self):
        self.running("A")
        (self.root / "lost-B").write_text("{}", encoding="utf-8")
        with mock.patch.object(launch, "_alive", return_value=True), \
                mock.patch.object(launch, "_listening", return_value=True):
            code, out = self.call(launch.url, wait=0, nonce="B")
        self.assertEqual((code, out["ok"], out["joined"]), (0, True, True))
        self.assertIn(":8766/", out["url"])
        self.assertFalse((self.root / "lost-B").exists())
        with mock.patch.object(launch, "_alive", return_value=True), \
                mock.patch.object(launch, "_listening", return_value=True):
            code, out = self.call(launch.url, wait=0, nonce="C")                  # 물러난 적 없는 nonce는 기다린다
        self.assertEqual((code, out["status"]), (1, "not_started"))

    def test_a_failure_is_written_only_by_the_owner(self):
        from app.store import LedgerBusy
        self.running("A")
        before = launch._paths()["state"].read_bytes()
        with mock.patch.object(launch.sys, "platform", "linux"), \
                mock.patch.object(launch, "serve", side_effect=LedgerBusy("busy")):
            self.assertEqual(launch.main(["serve", "--mock", "--nonce", "B"]), 1)
        self.assertEqual(launch._paths()["state"].read_bytes(), before)            # 소유자가 아니면 적지 않는다
        with mock.patch.object(launch.sys, "platform", "linux"), mock.patch.object(launch, "_OWNER", 99), \
                mock.patch.object(launch, "serve", side_effect=LedgerBusy("busy")):
            self.assertEqual(launch.main(["serve", "--mock", "--nonce", "B"]), 1)
        self.assertEqual((launch.read_state()["status"], launch.read_state()["nonce"]), ("failed", "B"))

    def test_stop_reaches_only_the_server_of_its_nonce(self):
        self.running("A", pid=os.getpid())
        with mock.patch.object(launch, "_alive", return_value=True):
            code, out = self.call(launch.stop, wait=0, nonce="B")
        self.assertEqual((code, out.get("not_owner")), (0, True))
        self.assertFalse((self.root / "stop-request").exists())
        with mock.patch.object(launch, "_alive", return_value=True):
            code, out = self.call(launch.stop, wait=0, nonce="A")
        self.assertEqual((self.root / "stop-request").read_text(encoding="utf-8"), str(os.getpid()))
        self.assertTrue(out.get("waiting_for_work"))

    def test_the_watch_ignores_a_request_for_another_server(self):
        stop_file = self.root / "stop-request"
        stop_file.write_text("1", encoding="utf-8")                                 # 다른 pid를 향한 요청
        server, controller = mock.Mock(), mock.Mock()
        controller.wait_idle.return_value = True
        watcher = threading.Thread(target=launch._watch, args=(server, controller, stop_file, 0.01), daemon=True)
        watcher.start()
        time.sleep(0.1)
        server.shutdown.assert_not_called()
        stop_file.write_text(str(os.getpid()), encoding="utf-8")                   # 이 서버를 향한 요청
        watcher.join(5)
        server.shutdown.assert_called_once_with()


class StartScriptTests(unittest.TestCase):
    SCRIPT = ROOT / "app" / "start.ps1"

    def test_the_script_is_ascii_for_windows_powershell_5_1(self):
        """PowerShell 5.1은 BOM 없는 UTF-8 스크립트를 ANSI로 읽는다 — 한글 안내는 \\u 이스케이프로 둔다."""
        data = self.SCRIPT.read_bytes()
        self.assertTrue(all(byte < 128 for byte in data), "app/start.ps1 must stay ASCII")

    @unittest.skipUnless(os.name == "nt" and shutil.which("powershell"), "Windows PowerShell parser")
    def test_the_script_parses(self):
        command = ("$e=$null; $t=$null; [System.Management.Automation.Language.Parser]::ParseFile("
                   f"'{self.SCRIPT}', [ref]$t, [ref]$e) | Out-Null; $e.Count")
        out = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True,
                             timeout=60)
        self.assertEqual(out.stdout.strip(), "0", out.stdout + out.stderr)

    def test_the_script_skips_ports_a_windows_program_already_holds(self):
        # 2026-09-27: Windows의 다른 서버가 8765를 쥐고 있어 앱 창이 그 프로그램을 열었다. 스크립트가 넘기는지 본다
        text = self.SCRIPT.read_text(encoding="ascii")
        self.assertIn("Get-NetTCPConnection -State Listen", text)
        self.assertIn("--avoid-ports", text)


class PortTests(unittest.TestCase):
    def test_ports_used_on_the_windows_side_are_skipped(self):
        self.assertEqual(launch.free_ports(""), list(launch.PORTS))
        self.assertEqual(launch.free_ports("8765, 8767"), [p for p in launch.PORTS if p not in (8765, 8767)])
        self.assertEqual(launch.free_ports(",".join(map(str, launch.PORTS))), [])
        for bad in ("8765;8766", "-1", "80a"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                launch.free_ports(bad)


if __name__ == "__main__":
    unittest.main()
