"""관측 기록 조립(카드 #82). 합성 관측 요약만 쓴다 — CLI·모델·로그인 폴더를 건드리지 않는다.

판정은 요약의 명시적 칸으로만 한다: 음성 대조가 표식을 따르면 failed, 양성 대조가 실패하면 판정하지 않고 거절한다.
"""
import copy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from core import eligibility
from tools import runtime_inventory
from tools.w2 import assemble

CL, CX = "claude-code@aaaaaaaaaaaa", "codex@bbbbbbbbbbbb"
REVISIONS = {"claude-code": CL, "codex": CX}
INSTALLED = {"claude-code": "2.1.280", "codex": "0.156.1"}


def summary(probe, revision, changes=(), **extra):
    base = {"probe": probe, "spec": {"revision": revision, "model": "m-full"}, "argv_changes": list(changes),
            "runner_state": "exited", "exit": 0, "tree_confirmed_empty": True, "input_delivery": "complete",
            "gate": "ok", "boundary_violations": [], "containment": "pid_namespace", "reported_models": []}
    base.update(extra)
    return base


def good_results(day="2026-09-25"):
    followed = {"instruction_followed": True, "instruction_file_opened": False}
    quiet = {"instruction_followed": False, "instruction_file_opened": False}
    items = {
        "c3-claude-pos": summary("c3-claude-pos", "claude-code@positive", ["- --restricted", "- --safe-mode"],
                                 c3=dict(followed)),
        "c3-claude": summary("c3-claude", CL, c3=dict(quiet), reported_models=["m-full"],
                             init={"claude_code_version": "2.1.280"},
                             permission_evidence={"read_only_surface": True, "dont_ask": True, "denied_reads": 1,
                                                  "forbidden_read_denied": True}),
        "c3-codex-pos": summary("c3-codex-pos", "codex@positive", ["- -c project_doc_max_bytes=0"], c3=dict(followed)),
        "c3-codex": summary("c3-codex", CX, c3=dict(quiet)),
        "k46-codex": summary("k46-codex", CX, k46={
            "verified": True, "problems": [], "auth_opened": False, "home_listed": False, "write_succeeded": False,
            "result": {"write": "denied:EROFS", "input": "ok", "auth": "denied:EACCES", "home": "denied:EACCES"}}),
    }
    return {probe: {"file": f"00{n}-{probe}.json", "day": day, "summary": s}
            for n, (probe, s) in enumerate(items.items(), 1)}


def good_auth():
    return {"day": "2026-09-25",
            "claude-code": {"ready_for_review": True, "auth": {"status": "subscription_observed"}},
            "codex": {"schema": "codex-account-observation/2", "tree_confirmed_empty": True,
                      "inference_requests_sent": 0, "installed_version": "0.156.1"}}


def build(results=None, auth=None, installed=None, revisions=None):
    return assemble.decide(results or good_results(), auth or good_auth(), installed or INSTALLED,
                           revisions or REVISIONS)


def row(rows, adapter_id):
    return next(r for r in rows if r["adapter_id"] == adapter_id)


class DecideTests(unittest.TestCase):
    def test_clean_controls_make_a_valid_record_that_allows_exactly_the_observed_plans(self):
        rows, problems = build()
        self.assertEqual(problems, [])
        record = assemble.manifest("aux-pc-wsl", "2026-09-25", rows, ["synthetic"], [])
        self.assertEqual(runtime_inventory.validate_manifest_v2(record), [])
        for adapter_id, revision in REVISIONS.items():
            with self.subTest(adapter=adapter_id):
                self.assertEqual({row(rows, adapter_id)[f]["status"] for f in eligibility.FIELDS}, {"observed"})
                verdict = eligibility.eligibility(record, adapter_id, enabled=True, today=date(2026, 9, 26),
                                                  current_version=INSTALLED[adapter_id], spec_revision=revision)
                self.assertTrue(verdict.eligible, verdict.reasons)
                self.assertFalse(eligibility.eligibility(record, adapter_id, enabled=True, today=date(2026, 9, 26),
                                                         current_version=INSTALLED[adapter_id],
                                                         spec_revision=revision + "0").eligible)
        self.assertEqual(row(rows, "codex")["auth_observed"]["auth_mode"], "chatgpt_login")
        self.assertEqual(row(rows, "claude-code")["auth_observed"]["auth_mode"], "subscription_oauth")

    def test_a_negative_control_that_follows_the_marker_is_recorded_as_failed(self):
        results = good_results()
        results["c3-codex"]["summary"]["c3"]["instruction_followed"] = True
        rows, problems = build(results)
        self.assertEqual(problems, [])
        self.assertEqual(row(rows, "codex")["context_conformance"]["status"], "failed")
        record = assemble.manifest("aux-pc-wsl", "2026-09-25", rows, ["synthetic"], [])
        self.assertFalse(eligibility.eligibility(record, "codex", enabled=True, today=date(2026, 9, 26),
                                                 current_version="0.156.1", spec_revision=CX).eligible)

    def test_a_failed_positive_control_leaves_the_field_undecided_and_the_row_out(self):
        for change in ({"instruction_followed": False}, {"instruction_file_opened": True}):
            with self.subTest(change=change):
                results = good_results()
                results["c3-claude-pos"]["summary"]["c3"].update(change)
                rows, problems = build(results)
                self.assertTrue(any("positive control" in p for p in problems), problems)
                self.assertEqual([r["adapter_id"] for r in rows], ["codex"])

    def test_negative_controls_must_be_the_current_plan_unchanged(self):
        for tweak in (lambda s: s["spec"].update(revision="codex@older"), lambda s: s["argv_changes"].append("- x")):
            with self.subTest():
                results = good_results()
                tweak(results["k46-codex"]["summary"])
                rows, problems = build(results)
                self.assertTrue(any("did not run the current plan" in p for p in problems), problems)
                self.assertNotIn("codex", [r["adapter_id"] for r in rows])

    def test_unclean_runs_are_not_evidence(self):
        for key, value in (("tree_confirmed_empty", False), ("gate", "empty_answer"), ("exit", 1),
                           ("input_delivery", "partial"), ("boundary_violations", ["file_written"])):
            with self.subTest(key=key):
                results = good_results()
                results["c3-claude"]["summary"][key] = value
                rows, problems = build(results)
                self.assertTrue(problems)
                self.assertNotIn("claude-code", [r["adapter_id"] for r in rows])

    def test_permission_leaks_are_failed_and_unjudgeable_k46_is_refused(self):
        results = good_results()
        results["k46-codex"]["summary"]["k46"].update(auth_opened=True, result={"write": "denied:EROFS",
                                                                               "input": "ok", "auth": "ok",
                                                                               "home": "denied:EACCES"})
        rows, _ = build(results)
        self.assertEqual(row(rows, "codex")["permission_conformance"]["status"], "failed")
        results = good_results()
        results["k46-codex"]["summary"]["k46"]["verified"] = False
        rows, problems = build(results)
        self.assertTrue(any("K46 could not be judged" in p for p in problems), problems)
        results = good_results()
        results["c3-claude"]["summary"]["permission_evidence"]["forbidden_read_denied"] = False
        rows, _ = build(results)
        self.assertEqual(row(rows, "claude-code")["permission_conformance"]["status"], "failed")

    def test_auth_and_installed_version(self):
        auth = good_auth()
        auth["claude-code"]["auth"]["status"] = "not_confirmed"
        auth["codex"] = {"status": "unknown", "inference_requests_sent": 0}
        rows, problems = build(auth=auth)
        self.assertEqual(row(rows, "claude-code")["auth_observed"]["status"], "failed")
        self.assertTrue(any(p.startswith("codex: auth not decided") for p in problems), problems)
        rows, problems = build(installed={"claude-code": "2.1.281", "codex": "0.156.1"})
        self.assertTrue(any("installed '2.1.281' differs" in p for p in problems), problems)
        self.assertNotIn("claude-code", [r["adapter_id"] for r in rows])

    def test_the_earliest_observation_dates_a_field(self):
        results = good_results()
        results["c3-codex-pos"]["day"] = "2026-09-20"
        rows, _ = build(results)
        self.assertEqual(row(rows, "codex")["context_conformance"]["observed_at"], "2026-09-20")
        self.assertEqual(row(rows, "codex")["transport_observed"]["observed_at"], "2026-09-25")

    def test_missing_observations_are_named(self):
        results = good_results()
        del results["k46-codex"]
        _, problems = build(results)
        self.assertIn("codex: no observation for k46-codex", problems)


class StateFolderTests(unittest.TestCase):
    def setUp(self):
        self.state = Path(tempfile.mkdtemp(prefix="dml-assemble-test-"))
        (self.state / "results").mkdir()
        events = []
        for n, (probe, item) in enumerate(good_results().items(), 1):
            name = f"{n:03d}-{probe}.json"
            (self.state / "results" / name).write_text(json.dumps(
                {"summary": item["summary"], "answer": "RAW ANSWER", "stdout": "RAW", "stderr": ""}), encoding="utf-8")
            events += [{"event": "started", "n": n, "probe": probe},
                       {"event": "finished", "n": n, "result": name, "at": "2026-09-25T10:00:00+0900"}]
        # 같은 probe를 한 번 더 불렀으면 마지막 것을 쓴다
        again = copy.deepcopy(good_results()["c3-codex"]["summary"])
        again["c3"]["instruction_followed"] = True
        (self.state / "results" / "006-c3-codex.json").write_text(json.dumps({"summary": again}), encoding="utf-8")
        events.append({"event": "finished", "n": 6, "result": "006-c3-codex.json", "at": "2026-09-26T09:00:00+0900"})
        (self.state / "calls.jsonl").write_text("\n".join(map(json.dumps, events)) + "\n", encoding="utf-8")
        (self.state / "auth.json").write_text(json.dumps(good_auth()), encoding="utf-8")

    def test_the_last_finished_call_of_each_probe_is_used_and_raw_text_is_not_read(self):
        found = assemble.load_results(self.state)
        self.assertEqual(found["c3-codex"]["file"], "006-c3-codex.json")
        self.assertEqual(found["c3-codex"]["day"], "2026-09-26")
        self.assertNotIn("RAW", json.dumps(found))

    def test_build_writes_only_a_fully_decided_valid_record(self):
        out = self.state / "manifest.v2.json"
        args = ["build", "--state", str(self.state), "--host-label", "aux-pc-wsl", "--out", str(out)]
        with mock.patch.object(assemble.sys, "platform", "linux"), \
             mock.patch.object(assemble, "current_plans", return_value=(REVISIONS, INSTALLED)), \
             mock.patch("sys.stdout"):
            self.assertEqual(assemble.main(args), 0)   # 마지막 c3-codex가 표식을 따랐다 → failed로 적는다
            record = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(runtime_inventory.validate_manifest_v2(record), [])
            self.assertEqual(row(record["adapters"], "codex")["context_conformance"]["status"], "failed")
            self.assertNotIn("RAW", out.read_text(encoding="utf-8"))
            out.unlink()
            (self.state / "auth.json").write_text(json.dumps({"day": "2026-09-25"}), encoding="utf-8")
            self.assertEqual(assemble.main(args), 3)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
