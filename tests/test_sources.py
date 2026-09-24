"""공통 자료 스냅샷(P0): 검사, 입력 digest에 묶기, 읽기 전용 사본, 시도마다의 해시 확인, 같은 판. 모델 호출 없음."""
from contextlib import closing
import hashlib
import http.client
import json
import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock

from app import controller as c
from app.report import build_report
from app.server import _Server, make_handler
from app.store import events
import test_app_cli_executor as cli_support
import test_app_controller as support

POLICY = "## 원격 근무(가상)\n- 주 2회까지\n- 표식: SRC-7Q3\n"


class Recording(support.SyntheticExecutor):
    """계획에 넘어온 입력 폴더와 그 안의 파일을 기록한다. 프로세스·모델 없음."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inputs = {}

    def plan(self, spec, prompt, work_dir, *, inputs=None):
        self.inputs[spec.pid] = inputs
        return super().plan(spec, prompt, work_dir)


class SourceTests(support.Base):
    def create(self, ctl, sources, pids=("a",)):
        return ctl.create_run("q", [support.cli(p) for p in pids], min_independent=1, sources=sources)

    def test_invalid_sources_are_refused_before_anything_is_stored(self):
        ctl = self.controller(Recording())
        for bad in ([("../x.md", "t")], [(".hidden", "t")], [("a/b.md", "t")], [("CON.txt", "t")], [("", "t")],
                    [("a" * 81, "t")], [("a.md", "t"), ("A.md", "u")], [("x.md", "a\x00b")], [("x.md", 3)],
                    [(f"f{i}.md", "t") for i in range(c.MAX_SOURCES + 1)],
                    [("big.md", "x" * (c.MAX_SOURCE_BYTES + 1))],
                    [(f"f{i}.md", "x" * c.MAX_SOURCE_BYTES) for i in range(5)], "not-a-list"):
            with self.subTest(bad=str(bad)[:40]):
                with self.assertRaises(c.ControllerError):
                    self.create(ctl, bad)
        self.assertEqual(self.store.rows("SELECT COUNT(*) AS n FROM runs")[0]["n"], 0)
        self.assertEqual(self.store.rows("SELECT COUNT(*) AS n FROM sources")[0]["n"], 0)

    def test_the_listing_is_bound_to_the_input_digest_and_the_content_stays_in_the_ledger(self):
        ex = Recording()
        ctl = self.controller(ex)
        rid = self.create(ctl, [("policy.md", POLICY), ("notes.txt", "메모")])
        self.assertTrue(ctl.wait_idle())
        view = self.run_view(ctl, rid)
        digest = hashlib.sha256(POLICY.encode("utf-8")).hexdigest()
        self.assertEqual(view["sources"][1], {"name": "policy.md", "sha256": digest, "bytes": len(POLICY.encode())})
        self.assertIn(f"policy.md ({len(POLICY.encode())} bytes, sha256 {digest})", view["prompt"])
        self.assertEqual(hashlib.sha256(view["prompt"].encode("utf-8")).hexdigest(), view["input_sha256"])
        self.assertNotIn("SRC-7Q3", json.dumps(view, ensure_ascii=False))   # 목록만, 내용은 화면에 없다
        created = next(e for e in events(self.store, rid) if e["kind"] == "run_created")
        self.assertEqual([s["name"] for s in created["sources"]], ["notes.txt", "policy.md"])
        self.assertEqual(build_report(ctl.view(rid), rid)["input"]["sources"], view["sources"])

    def test_participants_get_one_read_only_copy_and_runs_without_sources_keep_the_default(self):
        ex = Recording()
        ctl = self.controller(ex)
        rid = self.create(ctl, [("policy.md", POLICY)], pids=("a", "b"))
        self.assertTrue(ctl.wait_idle())
        root = ctl._source_root(rid)
        self.assertEqual(ex.inputs, {"a": (root,), "b": (root,)})
        self.assertEqual(Path(root, "policy.md").read_text(encoding="utf-8"), POLICY)
        self.assertIn(root, self.run_view(ctl, rid)["prompt"])
        if os.name == "posix":
            self.assertEqual(os.stat(Path(root, "policy.md")).st_mode & 0o222, 0)
        plain = self.create(ctl, None, pids=("c",))
        self.assertTrue(ctl.wait_idle())
        self.assertIsNone(ex.inputs["c"])
        self.assertEqual(self.run_view(ctl, plain)["sources"], [])

    def test_a_changed_snapshot_refuses_the_next_attempt_before_it_starts(self):
        for change in ("edit", "extra", "remove"):
            with self.subTest(change=change):
                ex = Recording(hold=("a",))
                ctl = self.controller(ex, max_parallel=1, unsettled_limit=2)
                rid = self.create(ctl, [("policy.md", POLICY)], pids=("a", "b"))
                self.assertTrue(support.wait_for(lambda: ex.started == ["a"]))
                path = Path(ctl._source_root(rid), "policy.md")
                if change == "edit":
                    os.chmod(path, 0o644)
                    path.write_text(POLICY.replace("2회", "5회"), encoding="utf-8")
                elif change == "extra":
                    Path(path.parent, "injected.md").write_text("다른 지시", encoding="utf-8")
                else:
                    os.chmod(path, 0o644)
                    path.unlink()
                ex.release("a")
                self.assertTrue(ctl.wait_idle())
                self.assertEqual(ex.started, ["a"])
                b = self.part(ctl, rid, "b")
                self.assertEqual((b["state"], b["status"]), (c.REJECTED, "process_failed_to_start"))
                self.assertIn("source snapshot changed", b["detail"])

    def test_the_http_api_passes_names_and_texts_only(self):
        controller = Mock()
        controller.executor.kind = "mock"
        controller.create_run.return_value = "r1"
        server = _Server(("127.0.0.1", 0), make_handler(controller, "token", 0))
        port = server.server_address[1]
        server.RequestHandlerClass = make_handler(controller, "token", port)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def post(body):
            with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=2)) as conn:
                conn.request("POST", "/api/runs", json.dumps(body), {"Content-Type": "application/json",
                                                                    "Authorization": "Bearer token"})
                return conn.getresponse().status
        base = {"question": "q", "participants": [{"pid": "claude"}], "min_independent": 1}
        self.assertEqual(post({**base, "sources": [{"name": "a.md", "text": "x"}]}), 200)
        self.assertEqual(controller.create_run.call_args.kwargs["sources"], [("a.md", "x")])
        for bad in ({"name": "a.md"}, {"name": "a.md", "text": "x", "path": "/etc"}, "a.md"):
            self.assertEqual(post({**base, "sources": [bad]}), 400)


@unittest.skipUnless(sys.platform == "linux", "uses Linux fake-install symlinks")
class RevisionTests(cli_support.Base):
    def test_a_source_folder_keeps_the_one_input_revision_whatever_its_path_or_content(self):
        for adapter in ("codex", "claude"):
            cli_support.install(self.home, adapter)
        empty, material = self.root / "empty", self.root / "material"
        empty.mkdir()
        material.mkdir()
        (material / "policy.md").write_text(POLICY, encoding="utf-8")
        ex = self.executor()
        work = str(self.root / "work")
        for spec in (cli_support.claude(), cli_support.codex()):
            with self.subTest(adapter=spec.adapter_id):
                self.assertEqual(ex.plan(spec, "q", work, inputs=(str(empty),)).revision,
                                 ex.plan(spec, "다른 질문", work, inputs=(str(material),)).revision)


if __name__ == "__main__":
    unittest.main()
