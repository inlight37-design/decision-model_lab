"""CLI entry point for the runtime's isolated, metadata-only Codex account probe."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.codex_account import main

if __name__ == "__main__":
    raise SystemExit(main())
