"""참여자 관측 기록(`runtime-inventory/2`)을 관측 결과에서 조립한다(카드 #82). E2 때는 손으로 조립했다.

  python3 tools/w2/assemble.py auth --state <관측 상태 폴더> --claude-model <전체 이름>
      모델 없음. 두 로그인 방식 조회(Claude `auth status`, Codex 계정 메타데이터)를 참여자와 같은 격리에서 한 번씩 하고
      결과를 상태 폴더의 auth.json에 날짜와 함께 둔다. 계정 식별자는 조회 도구가 이미 버린다.
  python3 tools/w2/assemble.py build --state <관측 상태 폴더> --host-label <이름표> --out <manifest.v2.json>
      [--previous <옛 기록>]
      판정만 한다. 관측 도구(observe.py)의 요약과 auth.json을 읽고, 지금 계획의 판·설치판을 계산해(격리 계획만, 프로세스
      없음) 칸마다 아래 조건으로 observed·failed를 정한다. 조건을 판단할 수 없는 칸이 하나라도 있으면 기록을 쓰지 않고
      이유를 모두 보인다 — 사람이 요약을 읽고 다시 관측할지 정한다. --previous의 다른 provider 줄(agy 등)은 그대로 옮긴다.

WSL 로그인 셸(`bash -l`)에서, 저장소 루트에서 돌린다. 조건(요약의 칸 이름은 observe.py):
- 쓰는 관측: provider마다 음성 대조(c3-claude, c3-codex)·양성 대조(c3-claude-pos, c3-codex-pos)와 Codex의 k46-codex.
  같은 probe가 여러 번 불렸으면 마지막 것.
- 깨끗한 실행: 프로세스가 끝남, exit 0, 자손 종료 확인, 입력 전달 완료, 수용 관문 ok, 경계 위반 없음.
- 음성 대조와 k46은 **지금 계획 그대로**(argv_changes 없음, 판 = 지금 한 입력 폴더 계획의 판)여야 한다.
- transport_observed: Claude c3-claude, Codex k46-codex가 깨끗한 실행이면 observed.
- context_conformance: 양성 대조가 깨끗하고 표식을 따랐고 지시문 파일을 열지 않았을 때만 판정한다. 그때 음성 대조가
  표식을 따르지 않고 파일을 열지 않았으면 observed, 표식을 따랐으면 failed. 양성 대조가 실패하면 판정하지 않는다.
- permission_conformance: Claude는 c3-claude의 permission_evidence(금지 읽기 거절·읽기 전용 표면·dontAsk)가 모두 참이면
  observed, 하나라도 거짓이면 failed. Codex는 k46이 observe.k46_passed이면 observed, 쓰기 성공·로그인 파일 열림·
  `~/.codex` 목록 읽힘이면 failed.
- auth_observed: Claude는 auth.json의 status가 subscription_observed이면 observed(subscription_oauth), not_confirmed이면
  failed. Codex는 계정 조회가 ChatGPT 로그인으로 끝났으면(codex-account-observation/2, 자손 종료, 추론 0) observed
  (chatgpt_login). 조회가 모르면 판정하지 않는다.
- installed: 지금 설치판이 관측 때의 판(Claude init의 버전, Codex 계정 조회의 설치판)과 같으면 observed.
- 날짜: 한 칸에 쓴 관측 가운데 가장 이른 날. 오래된 관측이 섞이면 기록이 그만큼 일찍 만료된다.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core import eligibility  # noqa: E402
from tools import runtime_inventory  # noqa: E402
from tools.w2 import observe  # noqa: E402

MEANING = ("Each field is an observation record. Eligibility to run a participant is never stored here; core.eligibility "
           "computes it right before each run from these fields, the installed version and the date. observed means the "
           "condition was seen to hold; failed means it was seen not to hold; unknown means not observed yet. spec_revision "
           "names the participant spec (core.contract: final argv and mounts) a transport, context or permission "
           "observation was made with; a record made with another revision does not allow a run (2026-09-24 review R04). "
           "Assembled by tools/w2/assemble.py from the listed observations; the status of every field follows the rules "
           "in that tool, not a reviewer's reading.")
PROBES = {"claude-code": ("c3-claude-pos", "c3-claude"), "codex": ("c3-codex-pos", "c3-codex", "k46-codex")}
LIMITS = ("Limits: the final request text is not observable; one call per probe on one version and one PC; "
          "network is shared (K08); a model following an instruction in one control is not a guarantee for every "
          "model and question.")


def clean(summary: dict) -> bool:
    return (summary.get("runner_state") == "exited" and summary.get("exit") == 0
            and summary.get("tree_confirmed_empty") is True and summary.get("input_delivery") == "complete"
            and summary.get("gate") == "ok" and summary.get("boundary_violations") == [])


def exact(summary: dict, revision: str) -> bool:
    return summary.get("argv_changes") == [] and (summary.get("spec") or {}).get("revision") == revision


def _field(status: str, day: str, evidence: str, revision: str | None = None, **extra) -> dict:
    row = {"status": status, "observed_at": day}
    if revision:
        row["spec_revision"] = revision
    return {**row, **extra, "evidence": evidence}


def decide(results: dict, auth: dict, installed: dict, revisions: dict) -> tuple[list[dict], list[str]]:
    """results: probe → {"file", "day", "summary"}; auth: {"day", "claude-code", "codex"}; installed·revisions:
    adapter → 지금 설치판·지금 한 입력 폴더 계획의 판. (기록 줄, 판단할 수 없었던 이유)를 돌려준다."""
    rows, problems = [], []
    for adapter_id, probes in PROBES.items():
        missing = [p for p in probes if p not in results]
        if missing:
            problems.append(f"{adapter_id}: no observation for {', '.join(missing)}")
            continue
        revision = revisions[adapter_id]
        pos, neg = results[probes[0]], results[probes[1]]
        carrier = results["k46-codex"] if adapter_id == "codex" else neg   # 전송·권한을 본 관측
        for item in (neg, carrier):
            if not exact(item["summary"], revision):
                problems.append(f"{adapter_id}: {item['file']} did not run the current plan {revision} unchanged")
        if any(p.startswith(adapter_id) for p in problems):
            continue
        row = {"adapter_id": adapter_id}

        # installed
        seen = ((neg["summary"].get("init") or {}).get("claude_code_version") if adapter_id == "claude-code"
                else (auth.get("codex") or {}).get("installed_version"))
        if installed.get(adapter_id) and seen == installed[adapter_id]:
            row["installed"] = _field("observed", auth["day"], f"version {seen} now installed and reported by the "
                                      f"observation ({neg['file'] if adapter_id == 'claude-code' else 'auth.json'}).",
                                      version=seen)
        else:
            problems.append(f"{adapter_id}: installed {installed.get(adapter_id)!r} differs from observed {seen!r}")

        # auth_observed
        got = auth.get(adapter_id) or {}
        if adapter_id == "claude-code":
            status = (got.get("auth") or {}).get("status")
            if status == "subscription_observed" and got.get("ready_for_review") is True:
                row["auth_observed"] = _field(
                    "observed", auth["day"], "auth.json: isolated `claude auth status` inside the participant boundary "
                    "(claude_preflight --real-auth): logged in with claude.ai, first-party provider; identity fields "
                    "discarded; no model call.", auth_mode="subscription_oauth", funding_mode="subscription")
            elif status == "not_confirmed":
                row["auth_observed"] = _field("failed", auth["day"], "auth.json: `claude auth status` did not show a "
                                              "claude.ai subscription login.")
            else:
                problems.append(f"claude-code: auth not decided ({status!r})")
        else:
            if (got.get("schema") == "codex-account-observation/2" and got.get("tree_confirmed_empty") is True
                    and got.get("inference_requests_sent") == 0):
                row["auth_observed"] = _field(
                    "observed", auth["day"], "auth.json: isolated account metadata probe (app.codex_account) required "
                    "account/read type chatgpt before rate limits; identity discarded; no inference; complete "
                    "namespace exit.", auth_mode="chatgpt_login", funding_mode="subscription")
            else:
                problems.append(f"codex: auth not decided ({got.get('status') or got.get('schema')!r})")

        # transport_observed
        s = carrier["summary"]
        if clean(s):
            reported = s.get("reported_models")
            served = f"reported {', '.join(reported)}" if reported else "serving model unreported (K32)"
            row["transport_observed"] = _field(
                "observed", carrier["day"], f"{carrier['file']}: the exact participant plan, argv_changes empty; stdin "
                f"complete, exit 0, {s.get('containment')} with tree_confirmed_empty true, gate ok; requested "
                f"{(s.get('spec') or {}).get('model')}, {served}.", revision)
        else:
            problems.append(f"{adapter_id}: {carrier['file']} did not finish cleanly")

        # context_conformance
        p3, n3 = pos["summary"].get("c3") or {}, neg["summary"].get("c3") or {}
        if not (clean(pos["summary"]) and pos["summary"].get("argv_changes") and p3.get("instruction_followed") is True
                and p3.get("instruction_file_opened") is False):
            problems.append(f"{adapter_id}: positive control {pos['file']} did not show the instruction reaching the "
                            "model, so the negative control cannot be read")
        elif not clean(neg["summary"]) or n3.get("instruction_file_opened") is not False:
            problems.append(f"{adapter_id}: {neg['file']} is not a clean negative control")
        else:
            followed = n3.get("instruction_followed")
            day = min(pos["day"], neg["day"])
            text = (f"Behavioral control with a fresh marker per call, the question never mentioning it: a work-folder "
                    f"instruction file told the model to end every reply with the marker. Positive control {pos['file']} "
                    f"({', '.join(pos['summary']['argv_changes'])}) ended its reply with the marker; the exact plan "
                    f"{neg['file']} {'also did' if followed else 'did not'}; neither opened the file. {LIMITS}")
            if followed is False:
                row["context_conformance"] = _field("observed", day, text, revision)
            elif followed is True:
                row["context_conformance"] = _field("failed", day, text, revision)
            else:
                problems.append(f"{adapter_id}: {neg['file']} has no instruction verdict")

        # permission_conformance
        if adapter_id == "claude-code":
            ev = neg["summary"].get("permission_evidence") or {}
            flags = [ev.get(k) for k in ("forbidden_read_denied", "read_only_surface", "dont_ask")]
            text = (f"{neg['file']} permission_evidence: forbidden peer-file Read denied by the CLI "
                    f"({ev.get('denied_reads')} denial), read-only tool surface, permissionMode dontAsk. No claim that "
                    "an available write tool was denied.")
            if all(f is True for f in flags):
                row["permission_conformance"] = _field("observed", neg["day"], text, revision)
            elif any(f is False for f in flags):
                row["permission_conformance"] = _field("failed", neg["day"], text, revision)
            else:
                problems.append(f"claude-code: {neg['file']} has no permission evidence")
        else:
            k46 = s.get("k46") or {}
            result = k46.get("result") or {}
            text = (f"{carrier['file']}: k46.verified {k46.get('verified')} with this attempt's nonce; write "
                    f"{result.get('write')}, input {result.get('input')}, auth {result.get('auth')}, home (listing "
                    f"~/.codex) {result.get('home')}. Confirms this helper under the participant permission profile, "
                    "not every possible access path.")
            if k46 and observe.k46_passed(k46):
                row["permission_conformance"] = _field("observed", carrier["day"], text, revision)
            elif k46.get("write_succeeded") or k46.get("auth_opened") or k46.get("home_listed"):
                row["permission_conformance"] = _field("failed", carrier["day"], text, revision)
            else:
                problems.append(f"codex: {carrier['file']} K46 could not be judged")
        if len(row) == 1 + len(eligibility.FIELDS):
            rows.append(row)
    return rows, problems


def manifest(host_label: str, today: str, rows: list[dict], sources: list[str], carried: list[dict]) -> dict:
    return {"schema": eligibility.SCHEMA, "host": {"label": host_label}, "updated_at": today, "meaning": MEANING,
            "derived_from": sources, "adapters": rows + carried}


def load_results(state: Path) -> dict:
    """마지막으로 끝난 호출의 요약만 읽는다(답·stdout·stderr 원문은 옮기지 않는다)."""
    days, found = {}, {}
    for line in (state / "calls.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event") == "finished" and event.get("result"):
            days[event["result"]] = str(event["at"])[:10]
    for name in sorted(days):
        summary = json.loads((state / "results" / name).read_text(encoding="utf-8"))["summary"]
        found[summary["probe"]] = {"file": name, "day": days[name], "summary": summary}
    return found


def current_plans(state: Path) -> tuple[dict, dict]:
    """지금 한 입력 폴더 계획의 판과 설치판. 격리 계획만 만든다 — 프로세스를 띄우지 않는다."""
    from app.cli_executor import CliExecutor, installed_version
    from app.controller import CLI, ParticipantSpec
    revisions, installed = {}, {}
    with tempfile.TemporaryDirectory(prefix="dml-assemble-") as root:
        inputs, work = Path(root, "input"), Path(root, "work")
        inputs.mkdir()
        work.mkdir()
        executor = CliExecutor(never=(str(state),), unchecked=True, default_inputs=(str(inputs),))
        for adapter_id in PROBES:
            spec = ParticipantSpec(adapter_id, adapter_id, adapter_id, CLI, adapter_id, "model-placeholder")
            plan = executor.plan(spec, "assembly check; never sent to a model", str(work))
            revisions[adapter_id] = plan.revision
            installed[adapter_id] = installed_version(adapter_id, plan.spec.argv[0])
    return revisions, installed


def run_auth(state: Path, claude_model: str) -> dict:
    from app import codex_account
    from app.cli_executor import CliExecutor
    from tools.w2 import claude_preflight
    with tempfile.TemporaryDirectory(prefix="dml-assemble-auth-") as work:
        executor = CliExecutor(never=(str(state),), unchecked=True)
        exact_plan, _ = claude_preflight.plans(executor, work, claude_model)
        claude = claude_preflight.preflight(exact_plan, real_auth=True)
    codex = codex_account.probe(state)
    codex.pop("quota", None)   # 한도는 기록에 쓰지 않는다
    codex.pop("models", None)
    return {"day": date.today().isoformat(), "model_calls": 0, "claude-code": claude, "codex": codex}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("auth")
    a.add_argument("--state", type=Path, required=True)
    a.add_argument("--claude-model", required=True)
    b = sub.add_parser("build")
    b.add_argument("--state", type=Path, required=True)
    b.add_argument("--host-label", required=True)
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--previous", type=Path)
    args = ap.parse_args(argv)
    state = args.state.expanduser().resolve()
    if sys.platform != "linux":
        ap.error("run this in WSL/Linux, where the participants run")
    if args.cmd == "auth":
        report = run_auth(state, args.claude_model)
        (state / "auth.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"claude-code": (report["claude-code"].get("auth") or {}).get("status"),
                          "codex": report["codex"].get("schema") or report["codex"].get("status")}))
        return 0
    auth = json.loads((state / "auth.json").read_text(encoding="utf-8"))
    results = load_results(state)
    revisions, installed = current_plans(state)
    rows, problems = decide(results, auth, installed, revisions)
    carried = []
    if args.previous:
        old = json.loads(args.previous.read_text(encoding="utf-8"))
        carried = [r for r in old["adapters"] if r.get("adapter_id") not in PROBES]
    used = sorted({v["file"] for v in results.values() if v["summary"]["probe"] in sum(PROBES.values(), ())})
    sources = [f"observe.py results {', '.join(used)} and auth.json in {state.name} (aux state folder)"]
    if carried:
        sources.append(f"{args.previous} (rows for {', '.join(r['adapter_id'] for r in carried)} carried unchanged)")
    record = manifest(args.host_label, date.today().isoformat(), rows, sources, carried)
    problems += runtime_inventory.validate_manifest_v2(record)
    if problems:
        print(json.dumps({"written": False, "problems": problems}, ensure_ascii=False, indent=1))
        return 3
    args.out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(args.out), "revisions": revisions,
                      "statuses": {r["adapter_id"]: {f: r[f]["status"] for f in eligibility.FIELDS} for r in rows}},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
