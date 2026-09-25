"""Build the blind grading pack for the D follow-up (card #60, 2026-09-25, aux-pc-wsl).

Reads view.json of each task run under --state. Accepted drafts are kept as written. A completed model synthesis
becomes one plain answer: recommendation, claims, disagreements, counterexample and unresolved points, without the
quoted draft text. Model and company names become [가림] and the HOME path becomes ~; nothing else changes. Every
answer gets a random name per task. Writes
  <out>/pack/<task>-<4 hex>.md and <out>/pack/rubric.md   the grading run's shared sources
  <out>/key.json                                         answer name -> task, condition, provider, run
and prints only the answer names, the counts and what is missing — never an answer or the key.

  python3 blind_pack.py --state ~/.local/state/dml-dfollow-20260925 --out ~/.local/state/dml-dfollow-20260925/blind
"""
import argparse, json, os, re, secrets, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 원장 폴더 → 과제, 초안의 조건. X는 같은 실행의 실제 합성이다.
RUNS = (("t1-px", "T1", "P"), ("t2-px", "T2", "P"), ("t4-s-codex", "T4", "S"), ("t4-s-claude", "T4", "S"),
        ("t4-px", "T4", "P"))
HIDE = re.compile(r"(?<![A-Za-z0-9])(?:codex|claude|anthropic|openai|chatgpt|gpt|sonnet|opus|haiku|luna)"
                  r"(?:-[A-Za-z0-9.]+)*(?![A-Za-z0-9])", re.IGNORECASE)
MODEL_SCHEMA = "a1-model-synthesis/1"


def hide(text):
    return HIDE.sub("[가림]", text.replace(os.path.expanduser("~"), "~"))


def render_synthesis(synthesis):
    """합성을 초안과 같은 한 편의 답으로 옮긴다. 인용(초안 원문)은 넣지 않는다 — 합성자가 쓴 문장만."""
    lines = ["권고: " + synthesis["card"]["recommendation"], "", "주장:"]
    lines += [f"- {item['statement']}" for item in synthesis["claims"]] or ["- (없음)"]
    lines += ["", "갈리는 점:"]
    lines += [f"- {item['topic']}" for item in synthesis["disagreements"]] or ["- (없음)"]
    counter = synthesis.get("strongest_counterexample")
    lines += ["", "결론을 뒤집을 조건: " + (counter["statement"] if counter else "(없음)"), "", "확인하지 못한 점:"]
    lines += [f"- {item}" for item in synthesis["unresolved"]] or ["- (없음)"]
    return "\n".join(lines) + "\n"


def answers(state: Path):
    """(과제, 조건, 제공자, 실행, pid, 글) 목록과 빠진 것."""
    found, missing = [], []
    for run_dir, task, condition in RUNS:
        path = state / run_dir / "view.json"
        if not path.is_file():
            missing.append(f"{run_dir}: no view.json")
            continue
        view = json.loads(path.read_text(encoding="utf-8"))
        if view.get("phase") != "revealed":
            missing.append(f"{run_dir}: not revealed")
            continue
        for part in view["participants"]:
            if part.get("state") == "accepted" and part.get("draft", "").strip():
                found.append((task, condition, part["pid"], run_dir, part["pid"], part["draft"]))
            else:
                missing.append(f"{run_dir}: {part['pid']} not accepted")
        if run_dir.endswith("-px"):
            synthesis = view.get("synthesis") or {}
            if synthesis.get("schema") == MODEL_SCHEMA and synthesis.get("status") == "completed":
                who = synthesis["synthesizer"]["adapter_id"]
                found.append((task, "X", "claude" if who == "claude-code" else who, run_dir, "synthesis",
                              render_synthesis(synthesis)))
            else:
                missing.append(f"{run_dir}: no completed model synthesis")
    return found, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", type=Path, required=True, help="experiment state folder holding the run ledgers")
    ap.add_argument("--out", type=Path, required=True, help="new folder for the pack and the key")
    args = ap.parse_args()
    if args.out.exists():
        sys.exit("the output folder must be new")
    found, missing = answers(args.state)
    pack = args.out / "pack"
    pack.mkdir(parents=True)
    key, names = {}, set()
    for task, condition, provider, run_dir, pid, text in found:
        name = f"{task}-{secrets.token_hex(2)}.md"
        while name in names:
            name = f"{task}-{secrets.token_hex(2)}.md"
        names.add(name)
        (pack / name).write_text(hide(text), encoding="utf-8")
        key[name] = {"task": task, "condition": condition, "provider": provider, "run": run_dir, "pid": pid}
    (pack / "rubric.md").write_text((HERE / "rubric.md").read_text(encoding="utf-8"), encoding="utf-8")
    (args.out / "key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                       encoding="utf-8")
    counts = {}
    for name in names:
        counts[name[:2]] = counts.get(name[:2], 0) + 1
    print(json.dumps({"answers": sorted(names), "counts": dict(sorted(counts.items())), "missing": missing},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
