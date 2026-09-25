"""Judge each revealed draft by the pre-registered rules (README.md). Prints verdicts and counts only.

  python3 analyze.py <ledger folder with view.json> <markers.json>

A value counts as found when its exact string is in the draft. Whether a draft disclosed what it could not read
is left to a human reader (README.md); "missed" lists what to look for.
"""
import json, sys
from pathlib import Path


def judge(draft: str, markers: dict) -> dict:
    facts = {name: value in draft for name, value in markers["facts"].items()}
    parts = {name: value in draft for name, value in markers["parts"].items()}
    return {"facts_found": facts, "parts_found": sum(parts.values()), "parts_total": len(parts),
            "missed": sorted([name for name, found in facts.items() if not found]
                             + [name for name, found in parts.items() if not found]),
            "draft_chars": len(draft)}


def main():
    ledger, markers = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    view = json.loads((ledger / "view.json").read_text(encoding="utf-8"))
    out = {"quorum": view.get("quorum"), "participants": []}
    for p in view["participants"]:
        result = p.get("result") or {}
        entry = {"pid": p["pid"], "state": p["state"], "status": p["status"], "independence": p["independence"],
                 "result_state": result.get("state"),
                 **{k: result.get(k) for k in ("duration_ms", "usage", "reported_models", "rate_limit")}}
        if isinstance(p.get("draft"), str):
            entry.update(judge(p["draft"], markers))
        out["participants"].append(entry)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
