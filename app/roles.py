"""A 단계 역할판의 고정 명세. 실행·봉인·예산은 기존 controller가 맡는다."""
from dataclasses import asdict


def freeze(board, participants, roster):
    """칸의 ID를 서버 명단으로 해석한다. 미지원 배치는 기록/호출보다 먼저 거절한다."""
    result = {"source": "legacy" if board is None else "board", "input_mode": "original",
              "supervisor": None, "orchestrator": None, "general": [],
              "isolated": [asdict(p) for p in participants]}
    if board is None:
        return result
    if not isinstance(board, dict) or set(board) != {
            "supervisor", "orchestrator", "isolated", "general", "input_mode"}:
        raise ValueError("역할판에는 네 칸과 입력 모드가 필요합니다.")
    if board["input_mode"] != "original":
        raise ValueError("다듬기는 슈퍼바이저 모델을 연결하는 다음 단계(D)에서 지원합니다.")
    for slot in ("supervisor", "orchestrator", "isolated", "general"):
        if not isinstance(board[slot], list) or any(not isinstance(pid, str) or pid not in roster
                                                   for pid in board[slot]):
            raise ValueError(f"{slot}: 현재 명단에 있는 참여자만 배치할 수 있습니다.")
    if board["supervisor"]:
        raise ValueError("슈퍼바이저 모델은 D 단계에서 지원합니다. 이 칸을 비우면 내가 맡습니다.")
    if board["general"]:
        raise ValueError("팀원(일반)은 C 단계에서 지원합니다. A 단계에서는 팀원(격리)를 사용하세요.")
    if len(board["orchestrator"]) > 1:
        raise ValueError("오케스트레이터는 한 장만 배치할 수 있습니다.")
    if board["isolated"] != [p.pid for p in participants]:
        raise ValueError("격리 칸과 실행 참여자가 다릅니다. 입력을 다시 확인하세요.")
    specs = [roster[pid] for slot in ("isolated", "orchestrator") for pid in board[slot]]
    if len({p.provider for p in specs}) != len(specs):
        raise ValueError("같은 provider 두 장은 아직 지원하지 않습니다. provider당 한 장만 배치하세요.")
    if board["orchestrator"]:
        spec = roster[board["orchestrator"][0]]
        if spec.transport != "cli":
            raise ValueError("A 단계 오케스트레이터는 CLI 합성자만 지원합니다. 원본 앱은 격리 칸에 놓으세요.")
        result["orchestrator"] = asdict(spec)
    return result


def task_projection(tasks, runs):
    """controller.view의 공개 투영만 받는다. 초안·결과·진행 시간은 목록으로 복사하지 않는다."""
    projected = []
    for task in tasks:
        timeline = []
        for run in sorted((r for r in runs if r["task_id"] == task["task_id"]), key=lambda r: r["created_at"]):
            gate, parts = run["gate"], run["participants"]
            synth = run.get("model_synthesis") or {}
            if any(p["state"] == "unknown" for p in parts) or synth.get("status") in ("unknown", "failed"):
                status, action = "problem", "종료·실패 확인"
            elif run["cancel_requested"] or gate["status"] == "quorum_blocked":
                status, action = "problem", "실행 확인"
            elif synth.get("status") == "running":
                status, action = "working", None
            elif gate["can_submit"] and any(p["state"] == "awaiting_user" for p in parts):
                status, action = "my_turn", "원본 앱 답 붙여넣기"
            elif gate["can_approve_reduction"]:
                status, action = "my_turn", "축소 여부 판단"
            elif gate["revealed"]:
                status, action = ("done", None) if run["reviewed"] else ("my_turn", "공개된 답 판단")
            else:
                status, action = "working", None
            timeline.append({"run_id": run["run_id"], "question": run["question"],
                             "created_at": run["created_at"], "role_config": run["role_config"],
                             "status": status, "action": action,
                             "calls_used": max(run["budget"]["used"], run["budget"]["reserved"])})
        latest = timeline[-1] if timeline else None
        status = next((s for s in ("problem", "my_turn", "working")
                       if any(r["status"] == s for r in timeline)), "done")
        projected.append({"task_id": task["task_id"], "title": task["title"], "created_at": task["created_at"],
                          "status": status, "role_config": latest["role_config"] if latest else None,
                          "calls_used": sum(r["calls_used"] for r in timeline), "runs": timeline})
    return projected
