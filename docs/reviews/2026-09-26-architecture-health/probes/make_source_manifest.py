"""Create/verify the fixed review's product-source manifest; no product writes.

Usage: python make_source_manifest.py REPO OUTPUT_JSON
The reference commit is deliberately fixed. A later checkout may contain review
documents, but the app/ and core/ file bytes must still match this review.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

REVIEW_SHA = "a232de7d4ae7de097dd014be5a791348b7881ea3"
SCHEMA = "dml-architecture-source-manifest/1"


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=repo, stderr=subprocess.PIPE)


def build_manifest(repo: Path) -> dict:
    resolved = git(repo, "rev-parse", "--verify", REVIEW_SHA + "^{commit}").decode().strip()
    if resolved != REVIEW_SHA:
        raise ValueError("the fixed review commit is not available")
    names = git(repo, "ls-tree", "-r", "--name-only", REVIEW_SHA, "--", "app", "core").decode().splitlines()
    if not names:
        raise ValueError("the fixed review commit has no product files")
    return {"schema": SCHEMA, "reviewed_sha": REVIEW_SHA, "algorithm": "sha256",
            "scope": "All tracked app/ and core/ files at the fixed commit; raw Git blob bytes (repository attributes require LF).",
            "files": {name: hashlib.sha256(git(repo, "show", f"{REVIEW_SHA}:{name}")).hexdigest() for name in names}}


def verify_sources(repo: Path, manifest: dict) -> dict:
    if manifest.get("schema") != SCHEMA or manifest.get("reviewed_sha") != REVIEW_SHA or manifest.get("algorithm") != "sha256":
        raise ValueError("source manifest is not for this fixed review")
    expected = manifest.get("files")
    if not isinstance(expected, dict) or not expected:
        raise ValueError("source manifest has no file hashes")
    present = set()
    for folder in ("app", "core"):
        for path in (repo / folder).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".pyc", ".pyo"):
                present.add(path.relative_to(repo).as_posix())
    changed = []
    for name, digest in expected.items():
        path = repo / name
        if not path.resolve().is_relative_to(repo) or path.is_symlink():
            changed.append({"path": name, "reason": "source path escaped repo or is a symlink"})
        elif not path.is_file():
            changed.append({"path": name, "reason": "missing"})
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            changed.append({"path": name, "reason": "SHA-256 differs from reviewed source"})
    for name in sorted(present - set(expected)):
        changed.append({"path": name, "reason": "additional product file"})
    if changed:
        raise ValueError("SOURCE CHANGED; probes were not authorized for this source: " + json.dumps(changed, ensure_ascii=True))
    return {"status": "verified", "reviewed_sha": REVIEW_SHA, "files_checked": len(expected),
            "checkout_head": git(repo, "rev-parse", "HEAD").decode().strip()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo", type=Path)
    ap.add_argument("output_json", type=Path)
    args = ap.parse_args()
    repo, output = args.repo.resolve(), args.output_json.resolve()
    if output.is_relative_to(repo):
        ap.error("write the manifest outside the product repository")
    manifest = build_manifest(repo)
    verified = verify_sources(repo, manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(output), **verified}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
