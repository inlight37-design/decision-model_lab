"""controller만 여는 작은 journal(SQLite). 초안도 여기에 봉인한다(인계 A1).

이 파일이 있는 폴더는 참여자 격리에 연결하지 않는다(core.isolation의 `never`). 해시는 접근 통제를 대신하지
않는다 — 봉인은 이 폴더를 참여자에게 보이지 않게 하는 것으로 성립한다.

사건(events)은 덧붙이기만 한다. 현재 상태(runs, participants, drafts)는 사건과 같은 거래에서 갱신한다.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY, created_at REAL NOT NULL, question TEXT NOT NULL, prompt TEXT NOT NULL,
  input_sha256 TEXT NOT NULL, input_bytes INTEGER NOT NULL, min_independent INTEGER NOT NULL,
  roster TEXT NOT NULL, reduction_approved INTEGER NOT NULL DEFAULT 0, note TEXT
);
CREATE TABLE IF NOT EXISTS participants (
  run_id TEXT NOT NULL, pid TEXT NOT NULL, spec TEXT NOT NULL, state TEXT NOT NULL,
  status TEXT, detail TEXT, result TEXT, PRIMARY KEY (run_id, pid)
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


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._db.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def tx(self) -> "_Tx":
        return _Tx(self)

    def rows(self, sql: str, *args: Any) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._db.execute(sql, args))

    def row(self, sql: str, *args: Any) -> sqlite3.Row | None:
        found = self.rows(sql, *args)
        return found[0] if found else None


class _Tx:
    """한 거래. 사건 하나와 그에 따른 상태 갱신을 함께 쓰거나 함께 버린다."""

    def __init__(self, store: Store) -> None:
        self.store = store

    def __enter__(self) -> "_Tx":
        self.store._lock.acquire()
        self.store._db.execute("BEGIN IMMEDIATE")
        return self

    def __exit__(self, kind, value, trace) -> None:
        try:
            self.store._db.execute("COMMIT" if kind is None else "ROLLBACK")
        finally:
            self.store._lock.release()

    def execute(self, sql: str, *args: Any) -> None:
        self.store._db.execute(sql, args)

    def event(self, run_id: str, kind: str, **payload: Any) -> None:
        seq = self.store._db.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM events WHERE run_id = ?",
                                     (run_id,)).fetchone()[0]
        self.store._db.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                               (run_id, seq, time.time(), kind, json.dumps(payload, ensure_ascii=False)))


def events(store: Store, run_id: str) -> Iterator[dict[str, Any]]:
    for row in store.rows("SELECT seq, at, kind, payload FROM events WHERE run_id = ? ORDER BY seq", run_id):
        yield {"seq": row["seq"], "at": row["at"], "kind": row["kind"], **json.loads(row["payload"])}
