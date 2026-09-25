"""관측 기록을 이 기기와 묶는다(카드 #71, 2026-09-25 외부 검토 R06). 공개 저장소에는 식별 값을 남기지 않는다.

관측 기록(manifest)은 한 기기에서 한 관측이다. 저장소를 다른 PC에 clone하고 CLI를 같은 판으로 설치하면 예전에는
그 기록으로 실제 실행(strict 포함)이 허가될 수 있었다 — 준비 조회가 기기를 비교하지 않았다. 이제 실제 모드의 준비
조회와 실행 직전 재검사는 "이 기기에서 이 기록을 관측했다"는 **로컬 등록**을 요구한다. 문맥 미확인 허용
(`--allow-context-unverified`)도 이 검사를 건너뛰지 않는다 — 그 옵션은 C3만 빼며 다른 기기의 인증·권한 관측을 빌리는
허가가 아니다.

등록은 사용자 상태 폴더의 파일 하나다(저장소 밖, 0600). 기록 파일의 sha256과 이 기기의 환경 지문을 짝짓는다.
지문은 /etc/machine-id를 이 앱 전용 키로 HMAC한 값에 호스트 이름·배포판·사용자 ID를 더해 다시 해시한 것이다 —
systemd가 권하는 앱별 유도 ID 방식이며 원래 machine-id는 저장하지 않는다. 호스트 이름을 바꾸거나 배포판을 다른
PC로 옮기면 다시 등록한다.

막는 것: 우발적인 다른 PC 재사용. 막지 못하는 것: VM·상태 폴더를 통째로 복제한 경우 — 원격 증명(attestation)이 아니다.
등록은 그 기기에서 관측을 마친 사람이 명시적으로 한다. clone했다고 자동으로 등록하지 않는다.

  python -m app.registration register <manifest.json> --host-label <기록의 host.label>
  python -m app.registration status <manifest.json>
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import hmac
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time

SCHEMA = "dml-registration/1"
_KEY = b"decision-model_lab/observation-registration/v1"


def registry_path() -> Path:
    override = os.environ.get("DML_REGISTRATION_FILE")
    if override:
        return Path(override)
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "decision-model-lab" / "registrations.json"


def fingerprint() -> str | None:
    """이 기기·배포판·사용자의 지문. machine-id가 없으면(Windows 등) None — 실제 참여자는 Linux에서만 돈다."""
    path = Path(os.environ.get("DML_MACHINE_ID_FILE", "/etc/machine-id"))
    try:
        machine = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError):
        return None
    if not machine:
        return None
    derived = hmac.new(_KEY, machine.encode("ascii"), hashlib.sha256).hexdigest()
    distro = os.environ.get("WSL_DISTRO_NAME", "")
    user = str(os.getuid()) if hasattr(os, "getuid") else getpass.getuser()
    return hashlib.sha256("|".join((SCHEMA, derived, socket.gethostname(), distro, user)).encode("utf-8")).hexdigest()


def digest(manifest: str | Path) -> str:
    return hashlib.sha256(Path(manifest).read_bytes()).hexdigest()


def _load() -> dict:
    try:
        data = json.loads(registry_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"schema": SCHEMA, "entries": []}
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("entries"), list):
        raise ValueError("the local registration file is not dml-registration/1")
    return data


def problem(manifest: str | Path) -> str | None:
    """이 기기에 등록된 기록이면 None, 아니면 거절 이유. 읽을 수 없으면 거절이다."""
    here = fingerprint()
    if here is None:
        return "this machine has no /etc/machine-id; observation records can only be registered on Linux/WSL"
    try:
        entries = _load()["entries"]
        mine = digest(manifest)
    except (OSError, ValueError) as exc:
        return f"cannot check the local registration ({type(exc).__name__})"
    matches = [e for e in entries if isinstance(e, dict) and e.get("manifest_sha256") == mine]
    if any(e.get("fingerprint") == here for e in matches):
        return None
    if matches:
        return "this observation record is registered on a different machine; observe here and register the new record"
    return ("this observation record is not registered on this machine — only a record observed here may be registered: "
            "python -m app.registration register <manifest> --host-label <label>")


def register(manifest: str | Path, host_label: str) -> dict:
    """이 기기에서 관측한 기록을 등록한다. 기록의 host.label이 맞아야 한다(다른 기기 기록을 잘못 고르는 것을 막는다)."""
    here = fingerprint()
    if here is None:
        raise ValueError("no /etc/machine-id: register on the Linux/WSL machine that made the observation")
    record = json.loads(Path(manifest).read_text(encoding="utf-8"))
    label = (record.get("host") or {}).get("label") if isinstance(record, dict) else None
    if label != host_label:
        raise ValueError(f"the record says host.label {label!r}, not {host_label!r}; register only records observed here")
    data = _load()
    entry = {"manifest_sha256": digest(manifest), "fingerprint": here, "host_label": host_label,
             "manifest_name": Path(manifest).name, "registered_at": int(time.time())}
    data["entries"] = [e for e in data["entries"]
                       if not (e.get("manifest_sha256") == entry["manifest_sha256"] and e.get("fingerprint") == here)]
    data["entries"].append(entry)
    path = registry_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        temp = Path(handle.name)
    if os.name != "nt":
        temp.chmod(0o600)
    os.replace(temp, path)
    return entry


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("register", help="이 기기에서 관측한 기록을 등록한다")
    reg.add_argument("manifest", type=Path)
    reg.add_argument("--host-label", required=True, help="기록의 host.label(확인용)")
    st = sub.add_parser("status", help="이 기기에서 기록이 쓰일 수 있는지 본다")
    st.add_argument("manifest", type=Path)
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.command == "register":
        try:
            entry = register(args.manifest, args.host_label)
        except (OSError, ValueError) as exc:
            print(f"not registered: {exc}", file=sys.stderr)
            return 1
        print(f"registered {entry['manifest_name']} (sha256 {entry['manifest_sha256'][:12]}…) on this machine "
              f"as {entry['host_label']}: {registry_path()}")
        return 0
    reason = problem(args.manifest)
    print("registered on this machine" if reason is None else f"not usable here: {reason}")
    return 0 if reason is None else 1


if __name__ == "__main__":
    sys.exit(main())
