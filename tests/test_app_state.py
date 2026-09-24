"""Row-backed membership, conditional transitions and irreversible journal migration."""
import hashlib
import json
import sqlite3
from unittest.mock import patch

from app import controller as c, store as s
import test_app_controller as support


class RunGateTests(support.Base):
    def manual_run(self):
        ctl = self.controller(support.SyntheticExecutor())
        rid = ctl.create_run("question", [support.manual("a"), support.manual("b")], min_independent=1,
                             quorum_policy=c.INCLUDE_UNVERIFIED)
        return ctl, rid, self.run_view(ctl, rid)["input_sha256"]

    def test_obsolete_roster_and_note_are_not_membership_authorities(self):
        ctl, rid, digest = self.manual_run()
        # An obsolete/corrupt cache must not resurrect rejected participants or prevent a valid reveal.
        with self.store.tx() as tx:
            tx.execute("UPDATE runs SET roster = ?, note = ? WHERE run_id = ?", "not current state", "stale", rid)
        ctl.submit_manual(rid, "a", "sealed answer", digest)
        sealed = self.run_view(ctl, rid)
        self.assertEqual(sealed["gate"]["status"], "waiting")
        self.assertIsNone(sealed["note"])
        self.assertNotIn("draft_sha256", self.part(ctl, rid, "a"))
        ctl.withdraw_manual(rid, "b")
        held = self.run_view(ctl, rid)
        self.assertEqual(held["gate"]["status"], "reduction_required")
        self.assertTrue(held["gate"]["can_approve_reduction"])
        self.assertFalse(held["gate"]["can_report"])
        ctl.approve_reduction(rid)
        opened = self.run_view(ctl, rid)
        self.assertEqual(opened["phase"], "revealed")
        self.assertTrue(opened["gate"]["can_report"])
        self.assertTrue(opened["gate"]["can_synthesize"])
        self.assertFalse(opened["gate"]["can_start"])
        self.assertEqual(self.part(ctl, rid, "a")["draft_sha256"],
                         hashlib.sha256(b"sealed answer").hexdigest())
        self.assertEqual(self.store.row("SELECT roster, note FROM runs WHERE run_id = ?", rid)[0], "not current state")

    def test_cancelled_rows_and_actions_are_consistent(self):
        ctl, rid, _digest = self.manual_run()
        ctl.cancel_run(rid)
        view = self.run_view(ctl, rid)
        self.assertEqual(view["gate"]["status"], "cancelled")
        for name, permitted in view["gate"].items():
            if name.startswith("can_"):
                self.assertFalse(permitted, name)
        self.assertEqual(view["quorum"]["counted"], 0)
        self.assertTrue(all(p["dropped"] for p in view["participants"]))
        self.assertTrue(all("packet" not in p for p in view["participants"]))

    def test_stale_manual_snapshot_cannot_replace_withdrawal_with_a_draft(self):
        ctl, rid, digest = self.manual_run()
        old = ctl._part(rid, "a")
        ctl.withdraw_manual(rid, "a")
        # Reproduce the audit's stale submit/withdraw order. The expected NULL attempt and
        # awaiting_user state no longer match, so neither a draft nor a sealed event is written.
        original = ctl._part
        with patch.object(ctl, "_part", side_effect=lambda run_id, pid: old if pid == "a" else original(run_id, pid)):
            with self.assertRaisesRegex(c.ControllerError, "duplicate"):
                ctl.submit_manual(rid, "a", "too late", digest)
        self.assertEqual(self.part(ctl, rid, "a")["state"], c.REJECTED)
        self.assertIsNone(self.store.row("SELECT 1 FROM drafts WHERE run_id = ? AND pid = 'a'", rid))
        self.assertNotIn("draft_sealed", [e["kind"] for e in s.events(self.store, rid)])

    def test_stale_withdrawal_cannot_drop_an_accepted_participant(self):
        ctl, rid, digest = self.manual_run()
        old = ctl._part(rid, "a")
        ctl.submit_manual(rid, "a", "kept", digest)
        with patch.object(ctl, "_part", return_value=old):
            ctl.withdraw_manual(rid, "a")
        self.assertEqual(self.part(ctl, rid, "a")["state"], c.ACCEPTED)
        self.assertFalse(self.part(ctl, rid, "a")["dropped"])
        self.assertNotIn("manual_withdrawn", [e["kind"] for e in s.events(self.store, rid)])
        ctl.submit_manual(rid, "b", "other", digest)
        self.assertEqual(self.run_view(ctl, rid)["phase"], "revealed")

    def test_unknown_acknowledgement_compares_attempt_as_well_as_state(self):
        ctl = self.controller(support.SyntheticExecutor(), max_parallel=0)
        rid = ctl.create_run("question", [support.cli("a")], min_independent=1)
        with self.store.tx() as tx:
            tx.execute("UPDATE participants SET state = ?, attempt = 'old' WHERE run_id = ?", c.UNKNOWN, rid)
        old = ctl._part(rid, "a")
        with self.store.tx() as tx:
            tx.execute("UPDATE participants SET attempt = 'current' WHERE run_id = ?", rid)
        with patch.object(ctl, "_part", return_value=old):
            ctl.acknowledge_unknown(rid, "a")
        self.assertEqual(self.part(ctl, rid, "a")["state"], c.UNKNOWN)
        self.assertEqual(ctl.view()["slots"]["used"], 1)
        self.assertNotIn("unknown_acknowledged", [e["kind"] for e in s.events(self.store, rid)])


class PhaseMigrationTests(support.Base):
    def legacy_run(self, phase):
        ctl = self.controller(support.SyntheticExecutor())
        rid = ctl.create_run("question", [support.manual("a")], min_independent=1,
                             quorum_policy=c.INCLUDE_UNVERIFIED)
        ctl.submit_manual(rid, "a", "published", self.run_view(ctl, rid)["input_sha256"])
        self.store._db.execute("UPDATE runs SET roster = ? WHERE run_id = ?", (json.dumps({"phase": phase}), rid))
        self.store._db.execute("ALTER TABLE runs DROP COLUMN phase")
        self.store._db.execute("PRAGMA user_version = 3")
        path = self.store.path
        self.store.close()
        return path, rid

    def test_revealed_legacy_run_stays_revealed_and_is_not_cancelled_on_upgrade(self):
        path, rid = self.legacy_run("revealed")
        self.store = s.Store(path)
        self.addCleanup(self.store.close)
        ctl = self.controller(support.SyntheticExecutor())
        self.assertEqual(self.run_view(ctl, rid)["phase"], "revealed")
        self.assertEqual(self.part(ctl, rid, "a")["draft"], "published")
        with self.assertRaises(c.ControllerError):
            ctl.cancel_run(rid)
        self.assertEqual([e["kind"] for e in s.events(self.store, rid)].count("revealed"), 1)

    def test_malformed_phase_rolls_back_migration_and_releases_lock(self):
        path, _rid = self.legacy_run("unknown-phase")
        for _ in range(2):
            with self.assertRaisesRegex(s.StoreError, "malformed legacy run phase"):
                s.Store(path)
        db = sqlite3.connect(path)
        self.addCleanup(db.close)
        self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 3)
        self.assertNotIn("phase", [row[1] for row in db.execute("PRAGMA table_info(runs)")])
