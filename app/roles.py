"""역할판의 고정 명세. 실행·봉인·예산은 기존 controller가 맡는다.

한 실행은 격리 칸(봉인·정족수) 또는 일반 칸(사람이 나눈 일, 카드 #125) 가운데 한쪽만 쓴다. 둘을 섞는 것은 E 단계다.
"""
from dataclasses import asdict

from app import usage as token_usage
from app.state import CLI


def freeze(board, participants, roster):
    """칸의 ID를 서버 명단으로 해석한다. 미지원 배치는 기록/호출보다 먼저 거절한다. participants는 채운 쪽 칸
    (격리 또는 일반)의 실행 참여자다."""
    result = {"source": "legacy" if board is None else "board", "input_mode": "original",
              "supervisor": None, "orchestrator": None, "general": [],
              "isolated": [asdict(p) for p in participants]}
    if board is None:
        return result
    if not isinstance(board, dict) or set(board) != {
            "supervisor", "orchestrator", "isolated", "general", "input_mode"}:
        raise ValueError("역할판에는 네 칸과 입력 모드가 필요합니다.")
    if board["input_mode"] not in ("original", "refine"):
        raise ValueError("질문 입력 모드는 원문 또는 다듬기입니다.")
    for slot in ("supervisor", "orchestrator", "isolated", "general"):
        if not isinstance(board[slot], list) or any(not isinstance(pid, str) or pid not in roster
                                                   for pid in board[slot]):
            raise ValueError(f"{slot}: 현재 명단에 있는 참여자만 배치할 수 있습니다.")
    # 슈퍼바이저 모델은 다듬기(카드 #130)와 공개 뒤 다음 단계 제안(카드 #133)을 한다. 원문 모드에서는 제안만 한다.
    if len(board["supervisor"]) > 1:
        raise ValueError("슈퍼바이저는 한 장만 배치할 수 있습니다.")
    if board["supervisor"] and roster[board["supervisor"][0]].transport != CLI:
        raise ValueError("슈퍼바이저에는 CLI 카드만 놓을 수 있습니다. 원본 앱은 격리 칸에 놓으세요.")
    if board["input_mode"] == "refine" and not board["supervisor"]:
        raise ValueError("다듬기는 슈퍼바이저 칸에 모델이 있을 때만 고를 수 있습니다.")
    if len(board["orchestrator"]) > 1:
        raise ValueError("오케스트레이터는 한 장만 배치할 수 있습니다.")
    if board["general"]:
        if board["supervisor"]:
            raise ValueError("일반 팀원 작업의 다듬기는 아직 지원하지 않습니다. 격리 칸을 쓰거나 슈퍼바이저 칸을 비우세요.")
        return _freeze_general(board, participants, result, roster)
    if board["isolated"] != [p.pid for p in participants]:
        raise ValueError("격리 칸과 실행 참여자가 다릅니다. 입력을 다시 확인하세요.")
    specs = [roster[pid] for slot in ("isolated", "orchestrator") for pid in board[slot]]
    if len({p.provider for p in specs}) != len(specs):
        raise ValueError("같은 provider 두 장은 아직 지원하지 않습니다. provider당 한 장만 배치하세요.")
    if board["orchestrator"]:
        spec = roster[board["orchestrator"][0]]
        if spec.transport != CLI:
            raise ValueError("A 단계 오케스트레이터는 CLI 합성자만 지원합니다. 원본 앱은 격리 칸에 놓으세요.")
        result["orchestrator"] = asdict(spec)
    if board["supervisor"]:
        # 같은 provider의 격리 팀원은 막지 않는다 — 화면이 경고한다(RB-06). 예산은 provider 상한을 같이 쓴다.
        result["supervisor"], result["input_mode"] = asdict(roster[board["supervisor"][0]]), board["input_mode"]
    return result


def _freeze_general(board, participants, result, roster):
    """일반 팀원 작업: 사람이 나누고 모은다. 오케스트레이터 칸에 CLI 모델을 두면 일 나누기를 제안받을 수 있다(카드 #135)
    — 시작은 여전히 내가 한다. 팀원은 격리 팀원과 같은 관측된 CLI 계획으로 읽기만 한다."""
    if board["isolated"]:
        raise ValueError("격리 칸과 일반 칸을 한 실행에 함께 쓰는 것은 E 단계에서 지원합니다. 한쪽만 채우세요.")
    orchestrator = roster[board["orchestrator"][0]] if board["orchestrator"] else None
    if orchestrator is not None and orchestrator.transport != CLI:
        raise ValueError("일반 작업의 오케스트레이터에는 CLI 카드만 놓을 수 있습니다. 비우면 내가 나눕니다.")
    if board["general"] != [p.pid for p in participants]:
        raise ValueError("일반 칸과 실행 팀원이 다릅니다. 입력을 다시 확인하세요.")
    if any(p.transport != CLI for p in participants):
        raise ValueError("팀원(일반)에는 CLI 카드만 놓을 수 있습니다. 원본 앱은 격리 칸에 놓으세요.")
    if len({p.provider for p in participants}) != len(participants):
        raise ValueError("같은 provider 두 장은 아직 지원하지 않습니다. provider당 한 장만 배치하세요.")
    return {**result, "general": [asdict(p) for p in participants], "isolated": [],
            "orchestrator": asdict(orchestrator) if orchestrator else None}


def task_projection(tasks, runs, held=None):
    """controller.view의 공개 투영만 받는다. 초안·결과·진행 시간은 목록으로 복사하지 않는다.

    held는 controller가 대기 시도를 지금 시작하지 않는 이유다 — "paused"(재시작 뒤 사용자가 이어서 시작하라고 할
    때까지) 또는 "unsettled"(종료 미확인이 상한에 닿음). '작업 중'은 스스로 진행하는 것으로 확인된 상태에만 쓰고,
    표에 없는 상태는 사람이 확인한다(N3). 합성 실패는 사람이 그 결과 판을 판단 완료하면 끝남이 된다 — 실패 기록은
    실행의 합성 상태에 그대로 남는다.
    """
    projected = []
    grouped = {}
    for run in sorted(runs, key=lambda r: r["created_at"]):
        grouped.setdefault(run["task_id"], []).append(run)
    for task in tasks:
        timeline = []
        for run in grouped.get(task["task_id"], []):
            gate, parts = run["gate"], run["participants"]
            states = {p["state"] for p in parts}
            synth = (run.get("model_synthesis") or {}).get("status")
            # 다음 단계 제안도 합성처럼 본다: 끝났는지 모르면 문제, 도는 중이면 작업 중(Codex 교차검토, PR #134)
            asked = {p["state"] for p in run.get("proposals", [])}
            # 교차검토(#140)도 같다. 대기 중인 검토자는 멈춘 원장이면 내가 이어서 시작하고, 아니면 차례를 기다린다
            reviews = (run.get("cross_review") or {}).get("reviews", [])
            variants = run.get('answer_revisions', [])
            reviews = [*reviews, *variants, *(c for v in variants for c in v['rechecks'])]
            checked = {r["state"] for r in reviews}
            if run.get("mode") == "general":
                status, action = _general_status(run, states, held)
            elif ("unknown" in states or synth == "unknown" or "unknown" in asked or "unknown" in checked
                  or (synth == "failed" and not run["reviewed"])):
                status, action = "problem", "종료·실패 확인"
            elif run["cancel_requested"] or gate["status"] == "quorum_blocked":
                status, action = "problem", "실행 확인"
            elif "queued" in checked and held == "paused":
                status, action = "my_turn", "멈춘 교차검토 이어서 시작"
            elif synth == "running" or "running" in asked or checked & {"running", "queued"}:
                status, action = "working", None
            elif gate["can_submit"] and "awaiting_user" in states:
                status, action = "my_turn", "원본 앱 답 붙여넣기"
            elif gate["can_approve_reduction"]:
                status, action = "my_turn", "축소 여부 판단"
            elif gate["revealed"]:
                status, action = ("done", None) if run["reviewed"] else ("my_turn", "공개된 답 판단")
            elif "queued" in states and held == "paused":
                status, action = "my_turn", "멈춘 시도 이어서 시작"
            elif "queued" in states and held == "unsettled":
                status, action = "problem", "종료 미확인 정리 뒤 시작"
            elif gate["status"] == "waiting" and states & {"running", "queued"}:
                status, action = "working", None
            else:
                status, action = "problem", "상태 확인"
            timeline.append({"run_id": run["run_id"], "question": run["question"],
                             "created_at": run["created_at"], "role_config": run["role_config"],
                             "status": status, "action": action,
                             # 실행에 묶인 다듬기 차례와 다음 단계 제안도 이 작업이 쓴 호출이다(2026-09-27 실제 확인에서
                             # 다듬기 차례가 빠진 것을 봄). 제안·결과 모으기의 실제 예약은 그 실행의 예약(reserved)에도
                             # 들어 있다
                             "calls_used": max(run["budget"]["used"] + len(run.get("model_syntheses", []))
                                               + len(run.get("proposals", [])) + len(run.get("collations", []))
                                               + sum(r["execution"] is not None for r in reviews),
                                               run["budget"]["reserved"])
                                           + len((run.get("refinement") or {}).get("turns", []))
                                           + (1 if run.get("split") else 0)})   # 일반 실행에 묶인 분담 제안(#135)
        latest = timeline[-1] if timeline else None
        if latest is None:
            continue  # 단일 실행 보고에는 그 실행의 작업만 싣는다.
        mine = grouped.get(task["task_id"], [])
        # 작업의 토큰 합계(카드 #141). 봉인 중인 실행은 합계가 없어 sealed_runs로만 센다
        tokens = token_usage.combine((r.get("usage") for r in mine), sealed=sum(r.get("usage") is None for r in mine))
        status = next((s for s in ("problem", "my_turn", "working")
                       if any(r["status"] == s for r in timeline)), "done")
        projected.append({"task_id": task["task_id"], "title": task["title"], "created_at": task["created_at"],
                          "status": status, "role_config": latest["role_config"] if latest else None,
                          "calls_used": sum(r["calls_used"] for r in timeline), "usage": tokens, "runs": timeline})
    return projected


def _general_status(run, states, held):
    """일반 실행의 작업 상태. 결과는 끝나는 대로 보이지만, 판단 완료는 모든 팀원이 끝나 모음으로 닫힌 뒤에 한다."""
    gate = run["gate"]
    gathered = {c["state"] for c in run.get("collations", [])}   # 결과 모으기도 제안처럼 본다(#137)
    if "unknown" in states or "unknown" in gathered:
        return "problem", "종료·실패 확인"
    if run["cancel_requested"]:
        return "problem", "실행 확인"
    if "running" in gathered:
        return "working", None
    if gate["collected"]:
        return ("done", None) if run["reviewed"] else ("my_turn", "결과 모아 판단")
    if "queued" in states and held == "paused":
        return "my_turn", "멈춘 시도 이어서 시작"
    if "queued" in states and held == "unsettled":
        return "problem", "종료 미확인 정리 뒤 시작"
    if gate["status"] == "waiting" and states & {"running", "queued"}:
        return "working", None
    return "problem", "상태 확인"
