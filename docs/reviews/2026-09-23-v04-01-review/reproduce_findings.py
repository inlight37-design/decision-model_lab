"""오프라인 재현. 실제 CLI, 계정, 환경변수, 설정 파일을 읽거나 실행하지 않는다.
사용법: python docs/reviews/2026-09-23-v04-01-review/reproduce_findings.py
관측 JSON을 출력하며 결함이 재현돼도 종료 0이다. 회귀 테스트 통과를 뜻하지 않는다.
"""
from __future__ import annotations
import ast
import copy
import importlib
import json
from pathlib import Path
import re
import sys


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root))
    inv = importlib.import_module("tools.runtime_inventory")
    source = (root / "tests/test_research_integrity.py").read_text(encoding="utf-8")
    namespace = {"re": re}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in {"RESTATED_COUNT", "COMMIT_SHA"}
                for t in node.targets):
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(root), "exec"), namespace)
    report = probe(inv, namespace["RESTATED_COUNT"], namespace["COMMIT_SHA"])
    print(json.dumps(report, ensure_ascii=False, indent=2))


def probe(inv, restated_count, commit_sha) -> dict:
    baseline = {"schema": "runtime-inventory/1", "tier": 2,
                "environment": {"mode": "fresh", "removed": []},
                "adapters": [{"adapter_id": "test", "configured": True,
                 "auth_mode": "subscription_oauth", "funding_mode": "subscription",
                 "capabilities": {"print": {"status": "observed", "evidence": "synthetic",
                                            "observed_at": "2026-09-23"}}}]}

    def check(m):
        try:
            errors = inv.validate_manifest(m)
            return {"accepted": not errors, "errors": errors}
        except Exception as exc:
            return {"exception": type(exc).__name__}

    cases = {"baseline": check(baseline)}
    for name, fields in (("missing_auth_funding", {}),
                         ("null_auth_funding", {"auth_mode": None, "funding_mode": None}),
                         ("empty_auth_funding", {"auth_mode": "", "funding_mode": ""})):
        m = copy.deepcopy(baseline)
        row = m["adapters"][0]
        row.pop("auth_mode")
        row.pop("funding_mode")
        row.update(fields)
        cases[name] = check(m)
    m = copy.deepcopy(baseline)
    m["adapters"][0]["installed"] = False
    cases["configured_but_not_installed"] = check(m)
    m = copy.deepcopy(baseline)
    m["adapters"][0]["capabilities"]["print"].update(evidence=True, observed_at=True)
    cases["boolean_evidence_date"] = check(m)
    m = copy.deepcopy(baseline)
    m["adapters"][0]["adapter_id"] = []
    cases["array_adapter_id"] = check(m)
    m = copy.deepcopy(baseline)
    m["env_presence"] = ["bad"]
    cases["array_env_presence"] = check(m)
    m = copy.deepcopy(baseline)
    m["env_presence"] = {"ANTHROPIC_API_KEY": {"present": True, "value": "FAKE_NON_TOKEN_SECRET"}}
    cases["unexpected_secret_value_field"] = check(m)
    env, removed = inv.fresh_environment(
        {"ANTHROPIC_BASE_URL": "https://injected.invalid", "PATH": "old"},
        {"Path": "system"},
        {"ANTHROPIC_BASE_URL": "https://expected.invalid", "CODEX_API_KEY": "FAKE", "Path": "user"})
    redact = inv.make_redactor(r"C:\Users\alice")
    fake_pat = "github_" + "pat_" + "A" * 82
    fake_google = "AI" + "za" + "A" * 35
    redaction = {"fine_grained_token_unchanged": redact(fake_pat) == fake_pat,
                 "google_token_redacted": redact(fake_google) != fake_google,
                 "other_user_with_space": redact(r"C:\Users\Jane Doe\notes.txt"),
                 "partial_user_path_flagged": bool(inv.USER_PATH.search(redact(r"C:\Users\Jane Doe\notes.txt")))}
    samples = ["전체 3개 provider를 지원한다", "검사 총 120개", "tests: 120", "63 commits", "120 tests"]
    counts = {s: bool(restated_count.search(s)) for s in samples}
    sha_line = "120 tests (unrelated source: " + "a" * 40 + ")"
    counts["unrelated_sha_line_skipped"] = bool(commit_sha.search(sha_line))
    return {"manifest": cases,
            "fresh_environment": {"retained_process_override": env.get("ANTHROPIC_BASE_URL") == "https://injected.invalid",
                                  "added_new_registry_key": "CODEX_API_KEY" in env,
                                  "path": env["PATH"], "removed": removed},
            "redaction": redaction, "count_guard": counts}


if __name__ == "__main__":
    main()
