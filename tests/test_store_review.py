"""Saved policy must fail closed; routine views must not scan unrelated event payloads."""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from app.store import SCHEMA_VERSION, Store, StoreError


class SavedBudgetReviewTests(unittest.TestCase):
    def test_invalid_saved_policy_is_refused_without_rewriting_it(self):
        policies = [
            (2, "null"), (2, "[]"), (2, "false"), (2, "1"), (2, '"codex"'),
            (2, "not-json"), (1.5, "{}"),
            *[(2, json.dumps(value)) for value in (
                {"codex": 0}, {"codex": -1}, {"codex": True}, {"codex": 1.5},
                {"codex": "1"}, {"": 1}, {"codex": None})],
        ]
        for cap, caps in policies:
            with self.subTest(cap=cap, caps=caps), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "journal.db"
                store = Store(path)
                with store.tx() as tx:
                    tx.execute("INSERT INTO live_budget VALUES (1, ?, ?)", cap, caps)
                    tx.event("saved-run", "live_call_reserved", cap=2, adapter_id="codex")
                store.close()
                store = Store(path)
                try:
                    before = tuple(store.row("SELECT * FROM live_budget"))
                    with self.assertRaises(StoreError):
                        store.bind_call_budget(None)
                    self.assertEqual(tuple(store.row("SELECT * FROM live_budget")), before)
                    self.assertEqual(len(store.rows("SELECT * FROM events")), 1)
                finally:
                    store.close()

    def test_valid_global_only_and_provider_limits_survive_restart(self):
        for caps in ({}, {"codex": 1, "claude-code": 1}):
            with self.subTest(caps=caps), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "journal.db"
                store = Store(path)
                self.assertEqual(store.bind_call_budget(2, caps), (2, caps))
                store.close()
                store = Store(path)
                try:
                    self.assertEqual(store.bind_call_budget(None), (2, caps))
                    self.assertEqual(store.bind_call_budget(2, caps), (2, caps))
                    with self.assertRaises(StoreError):
                        store.bind_call_budget(3, caps)
                finally:
                    store.close()


class JournalQueryReviewTests(unittest.TestCase):
    def test_kind_queries_use_an_index_and_preserve_event_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "journal.db")
            try:
                with store.tx() as tx:
                    for i in range(100):
                        tx.event("run", "other", ignored="x" * 100)
                    tx.event("run", "synthesis_started", attempt="one")
                    tx.event("run", "live_call_reserved", adapter_id="codex", cap=1)
                    tx.event("run", "synthesis_failed", attempt="one", result={})
                queries = (
                    "SELECT payload FROM events WHERE kind = 'live_call_reserved'",
                    "SELECT run_id, kind, payload FROM events WHERE kind IN "
                    "('synthesis_started', 'synthesis_failed', 'synthesis_completed', "
                    "'synthesis_unknown_acknowledged') ORDER BY run_id, seq",
                )
                for query in queries:
                    with self.subTest(query=query):
                        plan = " ".join(row[3] for row in store.rows("EXPLAIN QUERY PLAN " + query))
                        self.assertIn("SEARCH events", plan)
                        self.assertNotIn("SCAN events", plan)
                self.assertEqual([row["kind"] for row in store.rows(queries[1])],
                                 ["synthesis_started", "synthesis_failed"])
            finally:
                store.close()

    def test_index_install_is_idempotent_and_does_not_upgrade_wire_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal.db"
            store = Store(path)
            store.bind_call_budget(1, {"codex": 1})
            with store.tx() as tx:
                tx.execute("DROP INDEX IF EXISTS events_by_kind")
                tx.event("run", "live_call_reserved", adapter_id="codex", cap=1)
            store.close()
            for _ in range(2):
                store = Store(path)
                try:
                    self.assertEqual(store.row("PRAGMA user_version")[0], SCHEMA_VERSION)
                    self.assertEqual(store.bind_call_budget(None), (1, {"codex": 1}))
                    self.assertEqual(len(store.rows("SELECT * FROM events")), 1)
                    self.assertIn("events_by_kind", [row[1] for row in store.rows("PRAGMA index_list(events)")])
                finally:
                    store.close()
            # Connection.__exit__ handles transactions, not connection lifetime.
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("DROP INDEX events_by_kind")
                db.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
            with self.assertRaises(StoreError):
                Store(path)
            with closing(sqlite3.connect(path)) as db:
                self.assertNotIn("events_by_kind", [row[1] for row in db.execute("PRAGMA index_list(events)")])


if __name__ == "__main__":
    unittest.main()
