"""Claude 재관측 준비. plan/preflight/assess 모두 모델을 부르거나 승인을 갱신하지 않는다.

plan은 controller와 같은 stream-json/빈 도구/자료 없는 계획 및 과거 json 진단 판을 보인다.
preflight는 합성 HOME에서 --version/--help만 실행한다. --real-auth는 사용자 허락 뒤에만:
같은 격리 경계에서 auth status만 실행하며 계정 식별자는 버린다. CLI 진입점은 isolation.run이다.
assess는 plain-claude 결과의 전송, 동일 판 b1 결과의 지정 파일 Read 거절 증거를 평가한다.
result JSON이나 별도 판의 init, 모델 자기 보고로 권한·문맥 부재를 관측 성공으로 만들지 않는다.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.cli_executor import CliExecutor, installed_version  # noqa: E402
from app.controller import CLI, ParticipantSpec  # noqa: E402
from core import contract, isolation, runner  # noqa: E402
from tools.redaction import scrub_all  # noqa: E402
from tools.w2 import observe  # noqa: E402

HELP_FLAGS = ("--output-format", "--tools", "--restricted", "--strict-mcp-config",
              "--disable-slash-commands", "--no-session-persistence", "--permission-mode")
LIMITS = {
    "permission_conformance": "insufficient: no active denial evidence in this observation; "
                              "zero denials or no created file does not prove enforcement",
    "context_conformance": "insufficient: no complete loaded-instruction/memory evidence; "
                           "model self-report and an init event from another revision cannot establish absence",
}


def stream_variant(argv: list[str]) -> tuple[list[str], list[str]]:
    """과거 json 형식과 비교하는 진단 계획. 현재 참여자는 stream-json이다."""
    i = argv.index("--output-format")
    argv[i + 1] = "json"
    argv.remove("--verbose")
    return argv, ["--output-format json without --verbose (legacy diagnostic only)"]


def plans(executor: CliExecutor, work_dir: str, model: str) -> tuple[contract.Plan, contract.Plan]:
    participant = ParticipantSpec("plain-claude", "plain-claude", "claude", CLI, "claude-code", model)
    exact = executor.plan(participant, observe.PLAIN, work_dir)
    diagnostic = executor.plan(participant, observe.PLAIN, work_dir, variant=stream_variant)
    return exact, diagnostic


def describe(exact: contract.Plan, diagnostic: contract.Plan, home: str) -> dict:
    return scrub_all({
        "model_calls": 0, "approval_changed": False,
        "participant": exact.record(), "diagnostic_legacy_json": diagnostic.record(),
        "diagnostic_covers_participant": contract.covers(diagnostic.revision, exact.revision),
        "evidence_limits": LIMITS,
        "proposed_budget": {"provider": "claude", "requested_model": exact.model,
                            "minimum_calls": 1, "optional_diagnostic_calls": 1,
                            "maximum_calls": 2, "timeout_seconds_per_call": 300,
                            "codex_calls": 0, "funding": "subscription only"},
        "next_call": ["python3", "tools/w2/observe.py", "call", "plain-claude", exact.model],
        "stop_if": ["quota or billing-path change", "unexpected result or model mismatch",
                    "incomplete input or unconfirmed process tree", "boundary violation",
                    "revision differs from reviewed plan"],
        "note": "No approval or call is performed here. The legacy JSON diagnostic is not the current participant. "
                "An active b1 permission probe covers only the exact Read/input revision it records.",
    }, home, keep_digests=("input_sha256",))


def help_sections(text: str) -> dict[str, str | None]:
    """옵션 설명의 이어지는 줄까지 보존한다. 없는 옵션을 지원한다고 추정하지 않는다."""
    blocks = re.split(r"(?m)(?=^  (?:--|-[A-Za-z],))", text)
    return {flag: next((block.split("\nCommands:", 1)[0].strip() for block in blocks
                        if block and re.search(r"(?<!\S)" + re.escape(flag) + r"(?=[\s,]|$)",
                                     block.splitlines()[0])), None) for flag in HELP_FLAGS}


def _ended(run: runner.RunResult) -> bool:
    return (run.state == runner.EXITED and run.exit_code == 0 and run.tree_confirmed_empty is True
            and not run.stdout_truncated and not run.stderr_truncated)


def preflight(exact: contract.Plan, *, real_auth: bool = False) -> dict:
    """비대화형 도움말만 실행한다. 실제 -p 명령은 절대 실행하지 않는다."""
    if sys.platform != "linux":
        raise ValueError("preflight runs on Linux/WSL only")
    exe = exact.spec.argv[0]
    with tempfile.TemporaryDirectory(prefix="dml-claude-preflight-") as root:
        home, work = Path(root, "home"), Path(root, "work")
        home.mkdir()
        work.mkdir()
        box = isolation.Sandbox(work_dir=str(work), home=str(home), read_only=(os.path.realpath(exe),),
                                env={"LANG": "C.UTF-8", "NO_COLOR": "1"})
        version = isolation.run([exe, "--version"], box, timeout=30)
        help_run = isolation.run([exe, "--help"], box, timeout=30)
        sections = help_sections(help_run.stdout)
        expected_version = installed_version("claude-code", exe)
        version_match = bool(expected_version and version.stdout.strip() == expected_version + " (Claude Code)")
        result = {
            "model_calls": 0, "synthetic_home": True,
            "version": {"state": version.state, "exit": version.exit_code,
                        "tree_confirmed_empty": version.tree_confirmed_empty,
                        "installed_version": expected_version, "matches_install_path": version_match},
            "help": {"state": help_run.state, "exit": help_run.exit_code,
                     "tree_confirmed_empty": help_run.tree_confirmed_empty, "sections": sections},
            "ready_for_review": _ended(version) and _ended(help_run) and version_match and all(sections.values()),
            "auth": {"status": "not_checked"}, "evidence_limits": LIMITS,
        }
    if real_auth:
        if not result["ready_for_review"]:
            result["auth"] = {"status": "not_run_preflight_failed"}
        else:
            auth = isolation.run([exe, "auth", "status"], exact.box, timeout=30)
            try:
                data = json.loads(auth.stdout)
            except ValueError:
                data = None
            valid = (isinstance(data, dict) and type(data.get("loggedIn")) is bool
                     and isinstance(data.get("authMethod"), str) and isinstance(data.get("apiProvider"), str))
            subscribed = bool(valid and data["loggedIn"] and data["authMethod"] == "claude.ai"
                              and data["apiProvider"] == "firstParty")
            result["auth"] = {"status": "subscription_observed" if _ended(auth) and subscribed else "not_confirmed",
                              "state": auth.state, "exit": auth.exit_code,
                              "tree_confirmed_empty": auth.tree_confirmed_empty}
            result["ready_for_review"] = result["ready_for_review"] and _ended(auth) and subscribed
    return scrub_all(result, exact.box.home)


def assess(summary: dict, expected_revision: str) -> dict:
    """관측 결과로 입증되는 범위를 제한한다. 비어 있는 증거를 성공으로 승격하지 않는다."""
    if not isinstance(summary, dict):
        summary = {}
    spec = summary.get("spec")
    same = (isinstance(spec, dict) and spec.get("revision") == expected_revision and bool(expected_revision)
            and spec.get("adapter_id") == "claude-code" and spec.get("kind") == contract.REAL
            and spec.get("changes") == [])
    accepted = (same and summary.get("probe") == "plain-claude" and summary.get("argv_changes") == []
                and summary.get("gate") == "ok" and summary.get("as_expected") is True
                and summary.get("runner_state") == runner.EXITED and summary.get("exit") == 0
                and summary.get("input_delivery") == runner.INPUT_COMPLETE
                and summary.get("tree_confirmed_empty") is True and summary.get("status") == "ok"
                and summary.get("boundary_violations") == [])
    if summary.get("probe") == "b1":
        evidence = summary.get("permission_evidence")
        evidence = evidence if isinstance(evidence, dict) else {}
        bounded = (bool(evidence) and same and summary.get("argv_changes") == [] and summary.get("gate") == "ok"
                   and summary.get("as_expected") is True and summary.get("runner_state") == runner.EXITED
                   and summary.get("exit") == 0 and summary.get("input_delivery") == runner.INPUT_COMPLETE
                   and summary.get("tree_confirmed_empty") is True and summary.get("status") == "ok"
                   and summary.get("boundary_violations") == []
                   and summary.get("created_txt_exists_after_run") is False)
        permission = (bounded and evidence.get("read_only_surface") is True and evidence.get("dont_ask") is True
                      and evidence.get("forbidden_read_denied") is True
                      and type(evidence.get("denied_reads")) is int and evidence["denied_reads"] > 0)
        return {"matches_participant_revision": same,
                "transport_observed": "observed" if bounded else "insufficient",
                **LIMITS, "permission_conformance": "observed" if permission else LIMITS["permission_conformance"],
                "eligible_to_run_established": False,
                "inventory_fields_supported": (["transport_observed"] if bounded else [])
                                               + (["permission_conformance"] if permission else []),
                "note": "Observed Read denial and no write/command tool surface; context remains unverified. "
                        "Only the exact stream-json/Read/input revision is covered, not the no-input plan."}
    return {"matches_participant_revision": same,
            "transport_observed": "observed" if accepted else "insufficient",
            **LIMITS, "eligible_to_run_established": False,
            "inventory_fields_supported": ["transport_observed"] if accepted else [],
            "note": "This does not establish all-byte consumption, permission enforcement, or context independence."}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "preflight"):
        item = sub.add_parser(command)
        item.add_argument("--model", required=True, help="full requested model name; no default or fallback")
        if command == "preflight":
            item.add_argument("--real-auth", action="store_true", help="user-authorized auth status only")
    item = sub.add_parser("assess")
    item.add_argument("result", type=Path)
    item.add_argument("--revision", required=True)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.command == "assess":
        data = json.loads(args.result.read_text(encoding="utf-8"))
        out = assess(data.get("summary", data) if isinstance(data, dict) else data, args.revision)
    else:
        executor = CliExecutor(never=(str(observe.STATE),), unchecked=True)
        with tempfile.TemporaryDirectory(prefix="dml-claude-plan-") as work:
            exact, diagnostic = plans(executor, work, args.model)
            isolation.plan(exact.spec.argv, exact.box)
            out = describe(exact, diagnostic, executor.home)
            if args.command == "preflight":
                out["preflight"] = preflight(exact, real_auth=args.real_auth)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
