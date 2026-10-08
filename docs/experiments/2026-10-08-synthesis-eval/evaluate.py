"""합본(실제 합성) 품질 평가 — 2026-10-08 사전 등록의 실행·채점 도구. README.md가 절차다.

  python3 evaluate.py check-key                         정답 Q1–Q6을 코드로 다시 계산해 answers.json과 대조(모델 호출 없음)
  python3 evaluate.py configs --root <새 폴더>           과제마다 실제 설정(Codex 2·Claude 2, 빈 입력 폴더)
  python3 evaluate.py run --root <폴더> [--mock]          과제 Q1–Q8을 차례로 헤드리스 실행. 멈춤 조건에 걸리면 멈춘다
  python3 evaluate.py grade --root <폴더>                 Q1–Q6 자동 채점 → <폴더>/grades-auto.json
  python3 evaluate.py pack --root <폴더> --out <새 폴더>   Q7·Q8과 자동 채점이 판정하지 못한 답의 blind 묶음과 대응표
  python3 evaluate.py analyze --root <폴더> --manual <채점 JSON> --key <key.json>   지표와 결정 규칙

답 원문·원장·결과 JSON은 --root(저장소 밖)에만 둔다. 화면에는 답 원문을 찍지 않는다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MANIFEST = REPO / "docs/reviews/2026-09-26-main-pc-observe/manifest.v2.json"
MODELS = {"codex": "gpt-6-luna", "claude-code": "claude-sonnet-5"}
CAPS = {"codex": 2, "claude-code": 2}
TASKS = [f"Q{i}" for i in range(1, 9)]
AUTO = TASKS[:6]
CONDITIONS = ("S-codex", "S-claude", "X-codex", "X-claude")
STOP_PERCENT = 80
HIDE = re.compile(r"(?<![A-Za-z0-9])(?:codex|claude|anthropic|openai|chatgpt|gpt|sonnet|opus|haiku|luna)"
                  r"(?:-[A-Za-z0-9.]+)*(?![A-Za-z0-9])", re.IGNORECASE)
ANSWER = re.compile(r"^[ \t>*_-]*\**답\**[ \t]*[:：][ \t]*(.+?)[ \t]*$", re.MULTILINE)
ANSWER_INLINE = re.compile(r"답\**[ \t]*[:：][ \t]*(.+?)[ \t]*$", re.MULTILINE)   # 합성: 권고 문장 안의 '답:'도 본다


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def order(qid):
    """합성자 순서. 홀수 과제는 Codex 먼저, 짝수 과제는 Claude 먼저(순서 효과를 한쪽에 몰지 않는다)."""
    return "codex,claude-code" if int(qid[1:]) % 2 else "claude-code,codex"


# ---- 정답 -------------------------------------------------------------------------------------------------

def computed_key():
    from datetime import datetime
    from fractions import Fraction
    from itertools import product
    from zoneinfo import ZoneInfo
    kids = [(s, d) for s in "BG" for d in range(7)]
    seen = [c for c in product(kids, repeat=3) if any(s == "B" and d == 2 for s, d in c)]
    q2 = Fraction(sum(all(s == "B" for s, _ in c) for c in seen), len(seen))
    t = ([1, 2], 3)
    try:
        t[0] += [3]
        q3 = f"성공 {t}"
    except TypeError:
        q3 = f"오류 {t}"
    it = iter(range(10))
    pairs = list(zip(it, it, it))
    q4 = f"{len(pairs)} {next(it, '끝')}"

    def first_at_least(a, x):
        lo, hi = 0, len(a) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if a[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        return lo
    q5 = ", ".join(str(first_at_least([1, 3, 3, 5], x)) for x in (3, 6, 0))
    ny = ZoneInfo("America/New_York")
    q6 = str(datetime(2026, 3, 8, 3, 30, tzinfo=ny) - datetime(2026, 3, 8, 1, 30, tzinfo=ny))
    return {"Q1": f"{pow(3, 1000, 100000):05d}", "Q2": f"{q2.numerator}/{q2.denominator}", "Q3": q3, "Q4": q4,
            "Q5": q5, "Q6": q6}


def check_key(_):
    key, computed = load("answers.json"), computed_key()
    bad = {q: (key[q], computed[q]) for q in AUTO if key[q] != computed[q]}
    print(json.dumps(bad or "answers.json matches the computed answers", ensure_ascii=False))
    return 1 if bad else 0


# ---- 설정과 실행 -------------------------------------------------------------------------------------------

def configs(args):
    root = args.root.expanduser()
    if root.exists():
        sys.exit("the experiment folder must be new")
    folder = root / "configs"
    folder.mkdir(parents=True)
    for qid in TASKS:
        providers = []
        for adapter, cap in CAPS.items():
            empty = folder / f"in-{qid}-{adapter}"
            empty.mkdir()
            providers.append({"adapter_id": adapter, "model": MODELS[adapter], "inventory": str(MANIFEST),
                              "call_budget": cap, "input_dir": str(empty)})
        (folder / f"{qid}.json").write_text(json.dumps({"providers": providers}, indent=1) + "\n", encoding="utf-8")
    print(f"{len(TASKS)} configs in {folder}, caps {CAPS}")
    return 0


def percents(value):
    """계정 조회 JSON에서 '쓴 비율' 숫자를 모두 찾는다."""
    if isinstance(value, dict):
        for k, v in value.items():
            if "percent" in k.lower() and isinstance(v, (int, float)) and not isinstance(v, bool):
                yield float(v)
            else:
                yield from percents(v)
    elif isinstance(value, list):
        for v in value:
            yield from percents(v)


def rate_limits(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "rate_limit" and isinstance(v, dict):
                yield v
            else:
                yield from rate_limits(v)
    elif isinstance(value, list):
        for v in value:
            yield from rate_limits(v)


def ledger_rate_limits(ledger: Path):
    db = ledger / "journal.db"
    if not db.is_file():
        return []
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        found = []
        for (payload,) in conn.execute("SELECT payload FROM events"):
            try:
                found += list(rate_limits(json.loads(payload)))
            except ValueError:
                continue
        return found
    finally:
        conn.close()


def problems(rc, result, ledger, live):
    out = [] if rc == 0 else [f"exit code {rc}"]
    if result is None:
        return out + ["no result JSON"]
    if result.get("phase") != "revealed":
        out.append(f"phase {result.get('phase')}")
    out += [f"{p['pid']} {p['state']}/{p['status']}" for p in result.get("participants", []) if p["state"] != "accepted"]
    report = result.get("draft_report") or {}
    unknown = (((report.get("accounting") or {}).get("attempts") or {}).get("breakdown") or {}).get("unknown", 0)
    if unknown:
        out.append(f"{unknown} attempt(s) with unknown end")
    for request in result.get("synthesis_requests", []):
        if not request.get("started"):
            out.append(f"synthesis {request['synthesizer']} refused: {request.get('refused')}")
    if live:
        for limit in ledger_rate_limits(ledger):
            status = limit.get("status")
            if status != "allowed":
                out.append(f"Claude rate limit status {status!r}")
    return out


def summary(qid, result, seconds):
    """답 원문 없이 상태·시간·토큰만."""
    report = (result or {}).get("draft_report") or {}
    drafts = {p["pid"]: {"state": p["state"], "ms": (p.get("observation") or {}).get("duration_ms"),
                         "out_tokens": ((p.get("observation") or {}).get("usage") or {}).get("output_tokens")}
              for p in report.get("participants", [])}
    syntheses = [{"by": ((m.get("result") or {}).get("synthesizer") or {}).get("adapter_id"),
                  "status": (m.get("result") or {}).get("status") or m.get("status")}
                 for m in ((result or {}).get("decision_report") or {}).get("model_syntheses") or []]
    return {"task": qid, "phase": (result or {}).get("phase"), "wall_s": round(seconds, 1), "drafts": drafts,
            "syntheses": syntheses}


def run(args):
    root = args.root.expanduser()
    questions = load("questions.json")
    for folder in ("q", "ledgers", "results", "probes"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    log = root / "run-log.jsonl"
    for qid in ([args.only] if args.only else TASKS):
        ledger = root / "ledgers" / qid
        if ledger.exists():
            print(f"{qid}: ledger exists, never called twice — skipped")
            continue
        qfile = root / "q" / f"{qid}.txt"
        qfile.write_text(questions[qid], encoding="utf-8")
        out = root / "results" / f"{qid}.json"
        if args.mock:
            cmd = [sys.executable, "-m", "app.run", "--mock", "--policy", "include-unverified", "--synthesize", "mock"]
        else:
            probe_dir = root / "probes" / f"{qid}-data"
            probe_dir.mkdir()
            probe = subprocess.run([sys.executable, "-m", "app.codex_account", "--probe", "--data-dir", str(probe_dir)],
                                   cwd=REPO, capture_output=True, text=True, timeout=120)
            (root / "probes" / f"{qid}.json").write_text(probe.stdout, encoding="utf-8")
            try:
                used = max(percents(json.loads(probe.stdout)), default=None)
            except ValueError:
                used = None
            if probe.returncode != 0 or used is None or used >= STOP_PERCENT:
                print(f"STOP before {qid}: Codex account probe exit {probe.returncode}, highest used percent {used}")
                return 1
            cmd = [sys.executable, "-m", "app.run", "--live-config", str(root / "configs" / f"{qid}.json"),
                   "--policy", "independent-only", "--min-independent", "2", "--timeout", "180",
                   "--synthesize", "mock," + order(qid)]
        cmd += ["--data-dir", str(ledger), "--question-file", str(qfile), "--participants", "claude,codex",
                "--out", str(out)]
        start = time.monotonic()
        rc = subprocess.run(cmd, cwd=REPO).returncode
        seconds = time.monotonic() - start
        result = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else None
        line = summary(qid, result, seconds)
        line["problems"] = problems(rc, result, ledger, not args.mock)
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")
        print(json.dumps(line, ensure_ascii=False))
        if line["problems"]:
            print(f"STOP after {qid}: {line['problems']}")
            return 1
    return 0


# ---- 답 꺼내기와 자동 채점 ------------------------------------------------------------------------------------

def norm(text):
    text = text.replace("`", "").replace("**", "").replace(" ", " ")
    return re.sub(r"\s+", "", text).rstrip(".。").strip("'\"")


def answers_of(result):
    """조건 → (글, 메타). 초안은 원문 그대로, 합성은 합성자가 쓴 문장만(인용 제외)."""
    found, meta = {}, {}
    for p in (result.get("draft_report") or {}).get("participants", []):
        if p["state"] == "accepted":
            found[f"S-{p['pid']}"] = p["draft"]
    for m in (result.get("decision_report") or {}).get("model_syntheses") or []:
        res = m.get("result") or {}
        who = (res.get("synthesizer") or {}).get("adapter_id")
        cond = "X-claude" if who == "claude-code" else f"X-{who}"
        meta[cond] = {"status": res.get("status"), "labels": res.get("labels"), "checks": res.get("checks")}
        if res.get("status") == "completed":
            found[cond] = render_synthesis(res)
    return found, meta


def render_synthesis(s):
    lines = ["권고: " + s["card"]["recommendation"], "", "주장:"]
    lines += [f"- {c['statement']}" for c in s["claims"]] or ["- (없음)"]
    lines += ["", "갈리는 점:"] + ([f"- {d['topic']}" for d in s["disagreements"]] or ["- (없음)"])
    counter = s.get("strongest_counterexample")
    lines += ["", "결론을 뒤집을 조건: " + (counter["statement"] if counter else "(없음)"), "", "확인하지 못한 점:"]
    lines += [f"- {u}" for u in s["unresolved"]] or ["- (없음)"]
    return "\n".join(lines) + "\n"


def final_answer(text):
    hits = ANSWER.findall(text)
    return hits[-1] if hits else None


def grade_draft(text, correct):
    got = final_answer(text)
    if got is None:
        return {"verdict": "manual", "why": "no 답: line"}
    return {"verdict": "correct" if norm(got) == norm(correct) else "wrong", "answer": got}


def grade_synthesis(text, correct, wrong_candidates):
    """권고에 '답:' 줄이 있으면 그것으로, 없으면 권고와 주장에 나온 값으로 판정한다. 애매하면 사람 확인."""
    head = text.split("\n갈리는 점:")[0]   # 권고와 주장만. 갈리는 점에는 틀린 값이 원래 나온다
    hits = ANSWER_INLINE.findall(head)
    got = hits[-1] if hits else None
    if got is not None:
        return {"verdict": "correct" if norm(got) == norm(correct) else "wrong", "answer": got}
    body = norm(head)
    right = norm(correct) in body
    wrong = [w for w in wrong_candidates if norm(w) in body]
    if right and not wrong:
        return {"verdict": "correct", "why": "correct value only"}
    if wrong and not right:
        return {"verdict": "wrong", "why": "only a wrong draft value"}
    return {"verdict": "manual", "why": "both values" if right else "neither value"}


def grade(args):
    root = args.root.expanduser()
    key = load("answers.json")
    out = {}
    for qid in AUTO:
        path = root / "results" / f"{qid}.json"
        if not path.is_file():
            out[qid] = {"missing": True}
            continue
        found, meta = answers_of(json.loads(path.read_text(encoding="utf-8")))
        row = {}
        for cond in ("S-codex", "S-claude"):
            row[cond] = grade_draft(found[cond], key[qid]) if cond in found else {"verdict": "none"}
        wrong = [r["answer"] for r in row.values() if r.get("verdict") == "wrong"]
        for cond in ("X-codex", "X-claude"):
            if cond in found:
                row[cond] = grade_synthesis(found[cond], key[qid], wrong)
            else:
                row[cond] = {"verdict": "failed" if cond in meta else "none", "status": meta.get(cond, {}).get("status")}
        out[qid] = row
    (root / "grades-auto.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for qid, row in out.items():
        print(qid, {c: r.get("verdict") for c, r in row.items()} if "missing" not in row else "missing")
    return 0


# ---- blind 묶음 ----------------------------------------------------------------------------------------

def hide(text):
    return HIDE.sub("[가림]", text.replace(os.path.expanduser("~"), "~"))


def pack(args):
    root, out = args.root.expanduser(), args.out.expanduser()
    if out.exists():
        sys.exit("the output folder must be new")
    auto = json.loads((root / "grades-auto.json").read_text(encoding="utf-8"))
    (out / "pack").mkdir(parents=True)
    key, names = {}, set()
    for qid in TASKS:
        path = root / "results" / f"{qid}.json"
        if not path.is_file():
            continue
        found, _ = answers_of(json.loads(path.read_text(encoding="utf-8")))
        for cond, text in found.items():
            if qid in AUTO and auto[qid][cond]["verdict"] != "manual":
                continue
            name = f"{qid}-{secrets.token_hex(2)}"
            while name in names:
                name = f"{qid}-{secrets.token_hex(2)}"
            names.add(name)
            (out / "pack" / f"{name}.md").write_text(hide(text), encoding="utf-8")
            key[name] = {"task": qid, "condition": cond}
    (out / "pack" / "rubric.md").write_text((HERE / "rubric.md").read_text(encoding="utf-8"), encoding="utf-8")
    (out / "key.json").write_text(json.dumps(key, indent=1) + "\n", encoding="utf-8")
    print(f"{len(key)} answers in {out / 'pack'}; key.json is outside the pack — do not open it before grading")
    print(sorted(key))
    return 0


# ---- 지표와 결정 규칙 --------------------------------------------------------------------------------------

def scores(root, manual, key):
    """과제 → 조건 → 점수(0–1). 자동 채점 Q1–Q6, 사람 채점 Q7·Q8·애매한 답. 실패한 합성과 없는 답은 0."""
    auto = json.loads((root / "grades-auto.json").read_text(encoding="utf-8"))
    by_name = {(v["task"], v["condition"]): name for name, v in key.items()}
    table, kinds = {}, {}
    for qid in TASKS:
        row, kind = {}, {}
        for cond in CONDITIONS:
            if qid in AUTO and qid in auto and "missing" not in auto[qid]:
                verdict = auto[qid][cond]["verdict"]
                if verdict == "manual":
                    verdict = manual[by_name[(qid, cond)]]["verdict"]
                row[cond] = 1.0 if verdict == "correct" else 0.0
                kind[cond] = verdict
            elif (qid, cond) in by_name:
                item = manual[by_name[(qid, cond)]]
                row[cond] = sum(item[c] for c in ("C1", "C2", "C3", "C4", "C5")) / 5
                kind[cond] = "rubric"
            else:
                row[cond] = 0.0
                kind[cond] = "none"
        table[qid], kinds[qid] = row, kind
    return table, kinds


def analyze(args):
    root = args.root.expanduser()
    manual = json.loads(args.manual.expanduser().read_text(encoding="utf-8"))
    key = json.loads(args.key.expanduser().read_text(encoding="utf-8"))
    table, kinds = scores(root, manual, key)
    totals = {c: round(sum(table[q][c] for q in TASKS), 2) for c in CONDITIONS}
    best_single = max(totals["S-codex"], totals["S-claude"])
    splits = [q for q in TASKS if table[q]["S-codex"] != table[q]["S-claude"]]
    verdicts = {}
    for x in ("X-codex", "X-claude"):
        best = {q: max(table[q]["S-codex"], table[q]["S-claude"]) for q in TASKS}
        gains = [q for q in TASKS if table[q][x] > best[q]]
        losses = [q for q in TASKS if table[q][x] < best[q]]
        held = [q for q in TASKS if kinds[q][x] in ("manual", "held") and table[q][x] < best[q]]
        failed = [q for q in TASKS if kinds[q][x] in ("failed", "none")]
        if len(splits) < 3:
            rule = "판단 불가 — 갈린 과제가 3개 미만"
        elif len(gains) >= 2 and not losses and len(failed) <= 1 and totals[x] >= best_single:
            rule = "권고 후보 — 두 초안이 갈릴 때 이 합성자를 쓰라"
        elif losses and not gains:
            rule = "기본 끔 유지 — 손실만 있고 이득이 없다"
        else:
            rule = "미확립"
        verdicts[x] = {"total": totals[x], "gains": gains, "losses": losses, "held_or_manual_losses": held,
                       "failed_or_missing": failed, "rule": rule}
    result = {"scores": table, "kinds": kinds, "totals": totals, "best_single_total": best_single,
              "split_tasks": splits, "synthesizers": verdicts}
    (root / "analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-key")
    for name in ("configs", "run", "grade", "pack", "analyze"):
        p = sub.add_parser(name)
        p.add_argument("--root", type=Path, required=True)
        if name == "run":
            p.add_argument("--mock", action="store_true")
            p.add_argument("--only", choices=TASKS)
        if name == "pack":
            p.add_argument("--out", type=Path, required=True)
        if name == "analyze":
            p.add_argument("--manual", type=Path, required=True)
            p.add_argument("--key", type=Path, required=True)
    args = ap.parse_args()
    return {"check-key": check_key, "configs": configs, "run": run, "grade": grade, "pack": pack,
            "analyze": analyze}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
