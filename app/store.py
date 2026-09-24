"""controller만 여는 작은 journal(SQLite). 초안도 여기에 봉인한다(인계 A1).

이 파일이 있는 폴더는 참여자 격리에 연결하지 않는다(core.isolation의 `never`). 해시는 접근 통제를 대신하지
않는다 — 봉인은 이 폴더를 참여자에게 보이지 않게 하는 것으로 성립한다.

사건(events)은 덧붙이기만 한다. 현재 상태(runs, participants, drafts)는 사건과 같은 거래에서 갱신한다.

원장 하나를 여는 것은 한 번에 하나다. 열 때 옆의 잠금 파일을 배타적으로 잡고, 닫거나 프로세스가 죽으면
운영체제가 푼다. 같은 데이터 폴더로 서버를 하나 더 띄우면 원장을 건드리기 전에 여기서 멈춘다(A1 리뷰 A1-03).
스키마 버전은 `PRAGMA user_version`에 둔다. 0은 버전을 적기 전의 원장이고, 열 때 한 거래로 올린다.
이 코드보다 새 버전의 원장은 건드리지 않고 거절한다.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterator

# 1: participants.attempt. 2: runs.quorum_policy. 3: runs.cancel_requested(되돌리지 않는 실행 취소).
SCHEMA_VERSION = 3
SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY, created_at REAL NOT NULL, question TEXT NOT NULL, prompt TEXT NOT NULL,
  input_sha256 TEXT NOT NULL, input_bytes INTEGER NOT NULL, min_independent INTEGER NOT NULL,
  roster TEXT NOT NULL, reduction_approved INTEGER NOT NULL DEFAULT 0, note TEXT,
  quorum_policy TEXT NOT NULL DEFAULT 'include_unverified',
  cancel_requested INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS participants (
  run_id TEXT NOT NULL, pid TEXT NOT NULL, spec TEXT NOT NULL, state TEXT NOT NULL,
  status TEXT, detail TEXT, result TEXT, attempt TEXT, PRIMARY KEY (run_id, pid)
);
CREATE TABLE IF NOT EXISTS drafts (
  run_id TEXT NOT NULL, pid TEXT NOT NULL, text TEXT NOT NULL, sha256 TEXT NOT NULL,
  source TEXT NOT NULL, accepted_at REAL NOT NULL, PRIMARY KEY (run_id, pid)
);
CREATE TABLE IF NOT EXISTS events (
  run_id TEXT NOT NULL, seq INTEGER NOT NULL, at REAL NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
  PRIMARY KEY (run_id, seq)
);
"""


class LedgerBusy(RuntimeError):
    """다른 controller가 이 원장을 열고 있다. 원장과 토큰 파일은 바뀌지 않았다."""


class StoreError(RuntimeError):
    """원장을 열지 않았다(이 코드보다 새 스키마 등). 아무것도 바꾸지 않았다."""


def _lock(path: Path) -> int:
    """잠금 파일을 배타적으로 잡고 파일 기술자를 돌려준다. 기다리지 않는다."""
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        raise LedgerBusy(f"{path.parent} is already open by another controller") from None
    return fd


def _unlock(fd: int) -> None:
    if os.name == "nt":
        import msvcrt
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass   # 닫으면 운영체제가 푼다
    os.close(fd)


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_fd = _lock(self.path.with_name(self.path.name + ".lock"))
        try:
            self._db = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None)
            self._db.row_factory = sqlite3.Row
            self._lock = threading.RLock()
            self._migrate()
        except BaseException:
            if hasattr(self, "_db"):
                self._db.close()
            _unlock(self._lock_fd)
            raise

    def _migrate(self) -> None:
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                version = self._db.execute("PRAGMA user_version").fetchone()[0]
                if version > SCHEMA_VERSION:
                    raise StoreError(f"journal schema {version} is newer than this code ({SCHEMA_VERSION})")
                for statement in filter(str.strip, SCHEMA.split(";")):
                    self._db.execute(statement)
                if version < 1:
                    columns = {row[1] for row in self._db.execute("PRAGMA table_info(participants)")}
                    if "attempt" not in columns:
                        self._db.execute("ALTER TABLE participants ADD COLUMN attempt TEXT")
                if version < 2:
                    # 2 이전의 실행은 원본 앱 답도 정족수에 셌다 — 그 뜻을 바꾸지 않도록 그 정책으로 적는다
                    columns = {row[1] for row in self._db.execute("PRAGMA table_info(runs)")}
                    if "quorum_policy" not in columns:
                        self._db.execute("ALTER TABLE runs ADD COLUMN quorum_policy TEXT NOT NULL "
                                         "DEFAULT 'include_unverified'")
                if version < 3:
                    columns = {row[1] for row in self._db.execute("PRAGMA table_info(runs)")}
                    if "cancel_requested" not in columns:
                        self._db.execute("ALTER TABLE runs ADD COLUMN cancel_requested INTEGER NOT NULL DEFAULT 0")
                if version != SCHEMA_VERSION:
                    self._db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise

    def close(self) -> None:
        with self._lock:
            if self._lock_fd is None:
                return
            self._db.close()
            _unlock(self._lock_fd)
            self._lock_fd = None

    def tx(self) -> "_Tx":
        return _Tx(self)

    def rows(self, sql: str, *args: Any) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._db.execute(sql, args))

    def row(self, sql: str, *args: Any) -> sqlite3.Row | None:
        found = self.rows(sql, *args)
        return found[0] if found else None


class _Tx:
    """한 거래. 사건 하나와 그에 따른 상태 갱신을 함께 쓰거나 함께 버린다.

    거래 안에서 Store.rows()로 읽으면 같은 연결이므로 이 거래가 쓴 것까지 보인다.
    """

    def __init__(self, store: Store) -> None:
        self.store = store

    def __enter__(self) -> "_Tx":
        self.store._lock.acquire()
        try:
            self.store._db.execute("BEGIN IMMEDIATE")
        except BaseException:
            # __enter__가 실패하면 Python은 __exit__를 부르지 않는다.
            self.store._lock.release()
            raise
        return self

    def __exit__(self, kind, value, trace) -> None:
        try:
            try:
                self.store._db.execute("COMMIT" if kind is None else "ROLLBACK")
            except BaseException:
                # 지연 제약 등으로 COMMIT이 실패해도 다음 거래를 막는 열린 거래를 남기지 않는다.
                if self.store._db.in_transaction:
                    self.store._db.execute("ROLLBACK")
                raise
        finally:
            self.store._lock.release()

    def execute(self, sql: str, *args: Any) -> int:
        """바뀐 행 수를 돌려준다. 조건부 전이는 이것으로 기대한 상태가 아니었음을 안다."""
        return self.store._db.execute(sql, args).rowcount

    def event(self, run_id: str, kind: str, **payload: Any) -> None:
        seq = self.store._db.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM events WHERE run_id = ?",
                                     (run_id,)).fetchone()[0]
        self.store._db.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                               (run_id, seq, time.time(), kind, json.dumps(payload, ensure_ascii=False)))


def events(store: Store, run_id: str) -> Iterator[dict[str, Any]]:
    for row in store.rows("SELECT seq, at, kind, payload FROM events WHERE run_id = ? ORDER BY seq", run_id):
        yield {"seq": row["seq"], "at": row["at"], "kind": row["kind"], **json.loads(row["payload"])}
