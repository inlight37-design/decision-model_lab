"""Run this dated review's offline probes against its exact product source.

Usage: python -B run_probes.py REPO [--output-dir EXTERNAL_EMPTY_DIR] [--node NODE]
Default output is a retained external temporary directory. No model, account,
network, browser, or actual app/server is used. Successful counterexamples are
review evidence, not verification that the defects have been fixed.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
from make_source_manifest import REVIEW_SHA, verify_sources

HERE = Path(__file__).resolve().parent


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo", type=Path)
    ap.add_argument("--output-dir", type=Path)
    ap.add_argument("--manifest", type=Path, default=HERE / "source-manifest.json")
    ap.add_argument("--node", help="Node executable path/name; defaults to shutil.which('node')")
    args = ap.parse_args()
    repo = args.repo.resolve()
    output = args.output_dir.resolve() if args.output_dir else Path(tempfile.mkdtemp(prefix="dml-architecture-evidence-"))
    if output.is_relative_to(repo) or output == HERE:
        ap.error("output must be outside the product repository and the probe directory")
    if args.output_dir and output.exists() and any(output.iterdir()):
        ap.error("output directory must be new or empty; previous evidence is never overwritten")
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "probe-run.json"
    report = {"schema": "dml-architecture-probe-run/1", "reviewed_sha": REVIEW_SHA,
              "started_at": datetime.now(timezone.utc).isoformat(), "repo": str(repo), "output_dir": str(output),
              "python": {"version": platform.python_version(), "executable": sys.executable, "platform": platform.platform()},
              "node": None, "status": "running", "source_check": None, "stages": [],
              "meaning": "Successful counterexample reproduction and structural measurements; NOT fix verification or production safety/quality certification.",
              "scope": "Synthetic/mocked offline probes only; no provider/model CLI execution, account query, network, browser, or app server. Local Python, Node and read-only Git commands run the evidence."}
    save(report_path, report)
    try:
        manifest_path = args.manifest.resolve()
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        report["source_manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
        report["source_check"] = verify_sources(repo, manifest)
        node = shutil.which(args.node or "node")
        if node is None:
            raise ValueError("Node was not found; use --node PATH. No probes were run.")
        report["node"] = {"executable": node, "version": subprocess.check_output([node, "--version"], text=True, timeout=10).strip()}
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        scratch = output / "temporary"
        scratch.mkdir()
        env.update(TMP=str(scratch), TEMP=str(scratch), TMPDIR=str(scratch))
        stages = [
            ("controller", "controller-probes.py", [str(repo), str(output)], "controller-probe-results.json"),
            ("core", "core-probe.py", [str(repo), str(output)], "core-probe-results.json"),
            ("projection", "projection_probe.py", [str(repo), str(output / "projection-results.json")], "projection-results.json"),
            ("structure", "measure_structure.py", [str(repo), str(output / "structure.json")], "structure.json"),
            ("surface_python", "surface_probe.py", [str(repo)], None),
            ("surface_javascript", "surface_probe.cjs", [str(repo)], None),
        ]
        for name, script, arguments, result_file in stages:
            verify_sources(repo, manifest)
            script_path = HERE / script
            command = ([node] if script.endswith(".cjs") else [sys.executable, "-B"]) + [str(script_path), *arguments]
            entry = {"name": name, "script": script, "probe_sha256": hashlib.sha256(script_path.read_bytes()).hexdigest(),
                     "command": command, "status": "running"}
            report["stages"].append(entry)
            save(report_path, report)
            started = time.monotonic()
            try:
                result = subprocess.run(command, cwd=output, env=env, capture_output=True, text=True,
                                        encoding="utf-8", errors="replace", timeout=120)
                (output / f"{name}.stdout.txt").write_text(result.stdout, encoding="utf-8")
                (output / f"{name}.stderr.txt").write_text(result.stderr, encoding="utf-8")
                entry.update(returncode=result.returncode, elapsed_seconds=round(time.monotonic() - started, 3))
                if result.returncode:
                    raise RuntimeError(f"{name} exited {result.returncode}; see {name}.stderr.txt")
                result_path = output / (result_file or f"{name}-results.json")
                data = json.loads(result_path.read_text(encoding="utf-8") if result_file else result.stdout)
                if result_file is None:
                    save(result_path, data)
                entry.update(status="completed", result_file=result_path.name)
                verify_sources(repo, manifest)
            except Exception as exc:
                entry.update(status="failed", error=f"{type(exc).__name__}: {exc}",
                             elapsed_seconds=round(time.monotonic() - started, 3))
                raise
            finally:
                save(report_path, report)
        surface = {"baseline": REVIEW_SHA, "scope": report["scope"], "meaning": report["meaning"],
                   "python": json.loads((output / "surface_python-results.json").read_text(encoding="utf-8")),
                   "javascript": json.loads((output / "surface_javascript-results.json").read_text(encoding="utf-8"))}
        save(output / "surface-results.json", surface)
        if scratch.exists() and not any(scratch.iterdir()):
            scratch.rmdir()
        report["source_check_after"] = verify_sources(repo, manifest)
        report["status"] = "completed"
    except Exception as exc:
        report.update(status="aborted", error=f"{type(exc).__name__}: {exc}")
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        save(report_path, report)
    print(json.dumps({"status": report["status"], "reviewed_sha": REVIEW_SHA,
                      "report": str(report_path), "meaning": report["meaning"],
                      **({"error": report["error"]} if "error" in report else {})}, ensure_ascii=True))
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
