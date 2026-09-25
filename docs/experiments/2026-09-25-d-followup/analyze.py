"""Score the D follow-up from the blind grades (card #60, 2026-09-25).

Reads the key, the session's grades and the two model graders' drafts from the grading run's report.json, takes the
majority of the available graders per item and prints the pre-registered measures as JSON. A grader whose JSON
cannot be read is left out, not transcribed by hand. Never prints a draft; the graders' notes stay in the ledger.

  python3 analyze.py --blind <blind folder> --session grades-session.json --grade-report <grade ledger>/report.json \
      [--state <experiment state folder>]
"""
import argparse, json, sys
from collections import Counter
from pathlib import Path

ITEMS = {"T1": ("correct",), "T2": ("defect_ok", "fix_ok", "explanation_ok"), "T4": ("C1", "C2", "C3", "C4", "C5")}
OBJECTIVE_T4 = ("C1", "C2", "C3")
RUN_DIRS = ("t1-px", "t2-px", "t4-s-codex", "t4-s-claude", "t4-px", "grade")
SPLIT = "split"


def normalize(task, entry):
    """채점 한 항목을 판정 값으로 바꾼다. 모양이 다르면 ValueError."""
    if task == "T1":
        conclusion = entry["conclusion"]
        if isinstance(conclusion, bool) or not isinstance(conclusion, (str, int)):
            raise ValueError("conclusion")
        if not isinstance(entry["correct"], bool):
            raise ValueError("correct")
        return {"conclusion": str(conclusion).strip(), "correct": entry["correct"]}
    if task == "T2":
        out = {}
        for name in ("defect_ok", "explanation_ok"):
            if not isinstance(entry[name], bool):
                raise ValueError(name)
            out[name] = entry[name]
        if entry["fix_ok"] is not None and not isinstance(entry["fix_ok"], bool):
            raise ValueError("fix_ok")
        return {**out, "fix_ok": entry["fix_ok"]}
    out = {}
    for name in ITEMS["T4"]:
        value = int(entry[name]) if isinstance(entry[name], bool) else entry[name]
        if value not in (0, 1):
            raise ValueError(name)
        out[name] = int(value)
    relaxed = entry.get("relaxed", [])
    if not isinstance(relaxed, list):
        raise ValueError("relaxed")
    return {**out, "relaxed": sorted({int(x) for x in relaxed if str(x).strip().isdigit()})}


def grades_from(obj, key):
    """{"grades": [...]}에서 답안마다 판정을 읽는다. 모르는 파일·중복·모양 오류는 그 항목만 버리고 적는다."""
    if not isinstance(obj, dict) or not isinstance(obj.get("grades"), list):
        raise ValueError("no grades list")
    grades, errors = {}, []
    for entry in obj["grades"]:
        name = entry.get("file") if isinstance(entry, dict) else None
        if name not in key:
            errors.append(f"unknown file {name!r}")
            continue
        if name in grades:
            errors.append(f"duplicate {name}")
            grades.pop(name)
            continue
        try:
            grades[name] = normalize(key[name]["task"], entry)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{name}: bad {exc}")
    errors += [f"not graded {name}" for name in key if name not in grades and not any(name in e for e in errors)]
    return grades, errors


def json_objects(text):
    """글 안의 JSON 객체를 앞에서부터 모두 찾는다(코드 울타리 안팎 모두)."""
    decoder, index = json.JSONDecoder(), 0
    while (index := text.find("{", index)) >= 0:
        try:
            value, end = decoder.raw_decode(text, index)
        except ValueError:
            index += 1
            continue
        if isinstance(value, dict):
            yield value
        index = end


def model_grades(report, key):
    """채점 실행의 공개 초안에서 채점자마다 첫 번째 grades 객체를 읽는다."""
    found = {}
    for part in report.get("participants", []):
        name = part["pid"]
        if part.get("state") != "accepted":
            found[name] = {"status": f"not accepted ({part.get('status')})", "grades": {}, "errors": []}
            continue
        obj = next((o for o in json_objects(part["draft"]) if "grades" in o), None)
        if obj is None:
            found[name] = {"status": "unreadable", "grades": {}, "errors": ["no JSON object with grades"]}
            continue
        try:
            grades, errors = grades_from(obj, key)
            found[name] = {"status": "read", "grades": grades, "errors": errors}
        except ValueError as exc:
            found[name] = {"status": "unreadable", "grades": {}, "errors": [str(exc)]}
    return found


def majority(values):
    """있는 채점자의 값으로 과반을 정한다. 과반이 없으면 split, 채점자가 없으면 None."""
    if not values:
        return None
    counts = Counter(json.dumps(v) for v in values)
    top, count = counts.most_common(1)[0]
    return json.loads(top) if count * 2 > len(values) else SPLIT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blind", type=Path, required=True)
    ap.add_argument("--session", type=Path, required=True)
    ap.add_argument("--grade-report", type=Path, required=True)
    ap.add_argument("--state", type=Path, help="add each run's drive summary (usage, time, synthesis checks)")
    args = ap.parse_args()
    key = json.loads((args.blind / "key.json").read_text(encoding="utf-8"))
    session, session_errors = grades_from(json.loads(args.session.read_text(encoding="utf-8")), key)
    graders = {"session": {"status": "read", "grades": session, "errors": session_errors}}
    graders.update(model_grades(json.loads(args.grade_report.read_text(encoding="utf-8")), key))
    readable = [g for g, v in graders.items() if v["status"] == "read"]

    verdicts, per_grader, disagree = {}, {}, Counter()
    agreement = {f"{task}.{item}": [0, 0] for task, items in ITEMS.items() for item in items}
    for name, meta in sorted(key.items()):
        task = meta["task"]
        per_grader[name] = {g: graders[g]["grades"].get(name) for g in readable}
        row = {}
        for item in ITEMS[task] + (("conclusion",) if task == "T1" else ()):
            values = {g: v[item] for g, v in per_grader[name].items() if v is not None}
            row[item] = majority(list(values.values()))
            if item in ITEMS[task] and len(values) >= 2:
                agreement[f"{task}.{item}"][1] += 1
                agreement[f"{task}.{item}"][0] += len({json.dumps(v) for v in values.values()}) == 1
            if row[item] not in (None, SPLIT):
                for g, v in values.items():
                    disagree[g] += v != row[item]
        if task == "T4":
            row["total"] = sum(row[item] == 1 for item in ITEMS["T4"])
            row["splits"] = [item for item in ITEMS["T4"] if row[item] == SPLIT]
            row["relaxed"] = {g: v["relaxed"] for g, v in per_grader[name].items() if v is not None}
        verdicts[name] = {**meta, **row}

    def pick(task, condition, provider=None):
        return [v for v in verdicts.values() if v["task"] == task and v["condition"] == condition
                and (provider is None or v["provider"] == provider)]

    measures = {}
    p1, x1 = pick("T1", "P"), pick("T1", "X")
    right = [v["provider"] for v in p1 if v["correct"] is True]
    x = x1[0] if x1 else None
    # 합성이 없으면(실패·형식 오류) 손실이 아니라 "X 없음"이다. 과반이 없는(split) 값은 손실·갈림으로 세지 않는다.
    t1 = {"p_correct": {v["provider"]: v["correct"] for v in p1}, "oracle": bool(right), "x_missing": x is None,
          "x_conclusion": x and x["conclusion"], "x_correct": x and x["correct"],
          "loss": None if x is None else bool(right) and x["correct"] is False}
    if x is None:
        t1["l1"] = "no_synthesis"
    elif len(p1) == 2 and len(right) == 1:
        t1["l1"] = ("codex_synth_chose_the_other_family" if right == ["claude"] and x["correct"] is True else
                    "correct_side_is_the_synthesizer_family" if right == ["codex"] and x["correct"] is True else
                    "synthesis_loss" if x["correct"] is False else "split")
    else:
        t1["l1"] = "drafts_agree_or_none_correct_no_l1_judgment"
    measures["T1"] = t1

    p2, x2 = pick("T2", "P"), pick("T2", "X")
    x = x2[0] if x2 else None
    measures["T2"] = {"p": {v["provider"]: {k: v[k] for k in ITEMS["T2"]} for v in p2}, "x_missing": x is None,
                      "x": x and {k: x[k] for k in ITEMS["T2"]},
                      "defect_loss": None if x is None else
                      any(v["defect_ok"] is True for v in p2) and x["defect_ok"] is False,
                      "x_explanation_flaw": None if x is None else x["explanation_ok"] is False,
                      "p_explanation_flaw": [v["provider"] for v in p2 if v["explanation_ok"] is False]}

    drafts4 = pick("T4", "S") + pick("T4", "P")
    x4 = pick("T4", "X")
    x = x4[0] if x4 else None
    measures["T4"] = {
        "answers": {f"{v['condition']}-{v['provider']}": {**{k: v[k] for k in ITEMS["T4"]}, "total": v["total"],
                                                         "splits": v["splits"], "relaxed": v["relaxed"]}
                    for v in drafts4 + x4},
        "diverged_on_objective": {k: len({v[k] for v in drafts4 + x4 if v[k] in (0, 1)}) > 1 for k in OBJECTIVE_T4},
        "x_missing": x is None,
        "x_item_loss": [k for k in OBJECTIVE_T4
                        if x is not None and x[k] == 0 and any(v[k] == 1 for v in pick("T4", "P"))],
        "x_total": x and x["total"], "best_draft_total": max((v["total"] for v in drafts4), default=None)}

    family = {}
    for g in readable:
        totals = {"codex": [], "claude": []}
        for name, v in verdicts.items():
            grade = per_grader[name].get(g)
            if v["task"] == "T4" and v["condition"] in ("S", "P") and grade is not None:
                totals[v["provider"]].append(sum(grade[k] for k in ITEMS["T4"]))
        family[g] = {who: (round(sum(t) / len(t), 2) if t else None) for who, t in totals.items()}
    signal = None
    if {"codex", "claude"} <= set(family) and all(family[g][w] is not None for g in ("codex", "claude")
                                                   for w in ("codex", "claude")):
        signal = {"claude_grader_minus_codex_grader_on_claude_answers":
                  round(family["claude"]["claude"] - family["codex"]["claude"], 2),
                  "codex_grader_minus_claude_grader_on_codex_answers":
                  round(family["codex"]["codex"] - family["claude"]["codex"], 2)}
    measures["L3"] = {"graders_read": readable,
                      "grader_status": {g: {"status": v["status"], "errors": v["errors"]} for g, v in graders.items()},
                      "all_agree": {k: f"{a}/{n}" for k, (a, n) in agreement.items()},
                      "differs_from_majority": dict(disagree),
                      "t4_mean_total_by_author": family, "own_family_signal": signal}

    out = {"verdicts": verdicts, "per_grader": per_grader, "measures": measures}
    if args.state:
        runs = {}
        for run_dir in RUN_DIRS:
            path = args.state / run_dir / "drive-summary.json"
            if path.is_file():
                s = json.loads(path.read_text(encoding="utf-8"))
                runs[run_dir] = {k: s.get(k) for k in ("input_sha256", "input_bytes", "run_phase", "quorum",
                                                        "participants", "synthesis_status", "synthesis_checks",
                                                        "synthesizer", "live_call_budget", "server")}
        out["runs"] = runs
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
