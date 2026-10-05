"""Dated audit reproduction: synthetic preparation payload and ledger rollover.

Run from the repository checkout. Uses only temporary SQLite databases and the
existing synthetic test executor; no provider process or model is called. The
minimal ledger fixture tests selection policy only, not migration or recovery.
The default five preparations is comparable in number to one default provider
cap; twenty is a query stress fixture, not a claim about normal live operation.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from app.controller import Controller
from app.store import Store
from app import launch
from test_refine_mode import Refiner, ROSTER


def encoded(value):
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparations", type=int, choices=range(1, 21), default=5)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="dml-workflow-review-") as folder:
        root = Path(folder)
        store = Store(root / "journal.db")
        ctl = Controller(store, Refiner(), work_root=str(root / "work"))
        try:
            empty = ctl.queries.pages.browse(limit=1)
            original = "검토" * 3900
            ids = []
            for _ in range(args.preparations):
                ids.append(ctl.refine(ROSTER["claude"], original, use_memory=False))
                assert ctl.wait_idle()
            started = time.perf_counter()
            page = ctl.queries.pages.browse(limit=1)
            cold_ms = 1000 * (time.perf_counter() - started)
            started = time.perf_counter()
            warm = ctl.queries.pages.browse(limit=1)
            warm_ms = 1000 * (time.perf_counter() - started)
            print(json.dumps({"case": "unattached_refinement_projection",
                "refinements": len(page["refinements"]),
                "tasks": page["pages"]["tasks"]["total"],
                "page_limit": page["pages"]["tasks"]["limit"],
                "inbox": page["inbox"], "empty_bytes": encoded(empty),
                "body_bytes": encoded(page), "refinement_bytes": encoded(page["refinements"]),
                "warm_bytes": encoded(warm), "cold_ms": round(cold_ms, 3),
                "warm_ms": round(warm_ms, 3),
                "identical_requests_have_distinct_ids": len(set(ids)) == len(ids),
                "actual_model_calls": 0}, ensure_ascii=False))
        finally:
            assert ctl.shutdown()
            store.close()
        live = root / "live"
        previous = live / "20260101-000000"
        previous.mkdir(parents=True)
        db = sqlite3.connect(previous / "journal.db")
        try:
            db.executescript("CREATE TABLE live_budget (cap INTEGER, provider_caps TEXT); "
                             "CREATE TABLE events (kind TEXT, payload TEXT);")
            db.execute("INSERT INTO live_budget VALUES (?, ?)", (10, json.dumps(launch.CAPS)))
            for _ in range(5):
                db.execute("INSERT INTO events VALUES (?, ?)",
                           ("live_call_reserved", json.dumps({"adapter_id": "codex"})))
            db.commit()
        finally:
            db.close()
        chosen = launch.pick_ledger(live)
        print(json.dumps({"case": "one_provider_exhausted_rollover",
            "same_ledger_selected": chosen == previous,
            "previous_journal_preserved": (previous / "journal.db").exists(),
            "old_caps": launch.CAPS, "codex_reservations": 5,
            "claude_reservations": 0, "actual_model_calls": 0}))


if __name__ == "__main__":
    main()
