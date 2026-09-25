"""Write the live configs of the D follow-up (2026-09-25, aux-pc-wsl). No model call, no server.

Each config names the provider, the requested model, the observation manifest, a fresh empty input folder and the
call budget; the budget is fixed in a ledger the first time that ledger is used. Added after the runs, as the
record of how the configs were made (the pre-registered procedure did not change).

  python3 make_configs.py --root ~/.local/state/<new experiment folder>
"""
import argparse, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MANIFEST = REPO / "docs/reviews/2026-09-25-context-independence/manifest.v2.json"
MODELS = {"codex": "gpt-6-luna", "claude-code": "claude-sonnet-5"}
CONFIGS = {"px": {"codex": 2, "claude-code": 1}, "s-codex": {"codex": 1}, "s-claude": {"claude-code": 1},
           "grade": {"codex": 1, "claude-code": 1}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True, help="new experiment state folder")
    args = ap.parse_args()
    if args.root.exists():
        raise SystemExit("the experiment state folder must be new")
    configs = args.root / "configs"
    configs.mkdir(parents=True)
    for name, caps in CONFIGS.items():
        providers = []
        for adapter, cap in caps.items():
            empty = configs / f"in-{name}-{adapter}"
            empty.mkdir()
            providers.append({"adapter_id": adapter, "model": MODELS[adapter], "inventory": str(MANIFEST),
                              "call_budget": cap, "input_dir": str(empty)})
        (configs / f"{name}.json").write_text(json.dumps({"providers": providers}, indent=1) + "\n", encoding="utf-8")
        print(configs / f"{name}.json", {p["adapter_id"]: p["call_budget"] for p in providers})


if __name__ == "__main__":
    main()
