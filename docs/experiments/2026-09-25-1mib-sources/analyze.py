"""Judge each revealed draft by the pre-registered rules (README.md). Prints verdicts and counts only.

  python3 analyze.py <result.json from python -m app.run> <markers.json>

A value counts as found when its exact string is in the draft. Whether a draft disclosed what it could not read
is left to a human reader (README.md); "missed" lists what to look for. Drafts are not printed.
"""
import json, sys
from pathlib import Path

WHERE = ("front", "middle", "end")


def judge(draft: str, markers: dict) -> dict:
    facts = {name: value in draft for name, value in markers["facts"].items()}
    parts = {name: value in draft for name, value in markers["parts"].items()}
    by_place = {place: [0, 0] for place in WHERE}
    for index, name in enumerate(markers["facts"]):   # insertion order is front, middle, end per file
        by_place[WHERE[index % 3]][0] += facts[name]
        by_place[WHERE[index % 3]][1] += 1
    return {"facts_found": sum(facts.values()), "facts_total": len(facts),
            "by_place": {place: f"{found}/{total}" for place, (found, total) in by_place.items()},
            "parts_found": sum(parts.values()), "parts_total": len(parts),
            "missed": sorted([n for n, ok in facts.items() if not ok] + [n for n, ok in parts.items() if not ok]),
            "draft_chars": len(draft)}


def main():
    result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    markers = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    report = result.get("draft_report") or {}
    out = {"phase": result["phase"], "settled": result["settled"], "budget": result["budget"],
           "quorum": report.get("quorum"), "sources_bytes": sum(s["bytes"] for s in report.get("input", {}).get("sources", [])),
           "participants": []}
    drafts = {p["pid"]: p for p in report.get("participants", [])}
    for p in result["participants"]:
        entry = dict(p)
        item = drafts.get(p["pid"], {})
        observation = item.get("observation", {})
        entry["result_state"] = observation.get("state")
        entry.update({k: observation.get(k) for k in ("duration_ms", "usage", "reported_models",
                                                      "tree_confirmed_empty", "input_delivery")})
        if isinstance(item.get("draft"), str):
            entry.update(judge(item["draft"], markers))
        out["participants"].append(entry)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
