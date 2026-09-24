"""New runs must name their policy; legacy migrations preserve theirs."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.store import Store


class QuorumPolicyTests(unittest.TestCase):
    def test_new_journal_rejects_an_implicit_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "journal.db")
            try:
                with self.assertRaises(sqlite3.IntegrityError):
                    with store.tx() as tx:
                        tx.execute("INSERT INTO runs (run_id, created_at, question, prompt, input_sha256, "
                                   "input_bytes, min_independent, roster) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                   "r", 0, "q", "q", "hash", 1, 1, "{}")
                self.assertIsNone(store.row("SELECT * FROM runs"))
            finally:
                store.close()
