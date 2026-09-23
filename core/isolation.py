"""참여자 한 번의 실행을 bubblewrap으로 가둔다(인계 2절 16, W2). Linux·WSL2 전용, 표준 라이브러리만 쓴다.

보장하려는 것
- 파일: 참여자에게는 명시한 것만 보인다. 시스템 폴더(/usr, /etc와 병합된 /bin·/lib 링크)는 읽기 전용,
  HOME과 /tmp는 빈 tmpfs다. 입력 자료와 CLI 실행 파일은 읽기 전용, 작업 폴더와 그 CLI 자신의 설정·인증
  폴더만 쓰기다. 원장, 다른 참여자의 초안, 지난 합성, 다른 CLI의 인증, /mnt(Windows 드라이브), /run(WSL
  interop와 사용자 버스 소켓)은 연결하지 않는다. /etc 안의 링크가 밖을 가리키면(WSL의 resolv.conf →
  /mnt/wsl/resolv.conf) 그 파일 하나만 연결한다.
- 수명: 별도 PID namespace(--unshare-all에 포함)와 --die-with-parent. namespace의 첫 프로세스(bwrap의
  reaper)가 끝나면 커널이 안의 모든 프로세스를 끝내고, 그 첫 프로세스는 안이 빌 때까지 끝나지 않는다.
  그래서 runner는 bwrap의 프로세스 그룹이 빈 것으로 자손 전체의 종료를 확인한다(runner.PID_NAMESPACE).
- 환경: --clearenv 뒤 허용한 변수만 다시 넣는다.

보장하지 않는 것
- 네트워크. 모델 API가 필요해 공유한다(--share-net). 같은 네트워크 namespace의 localhost 포트와 abstract
  unix 소켓에는 닿는다 → controller 제어 API는 참여자에게 없는 토큰으로 막는다.
- 메모리·CPU 상한.
- CLI가 자기 설정·인증 폴더에서 무엇을 읽고 쓰는지. 토큰 갱신에 쓰기가 필요하다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import PurePosixPath
from typing import Mapping, Sequence

BWRAP = "/usr/bin/bwrap"
SYSTEM_READ_ONLY = ("/usr", "/etc")
MERGED_USR_LINKS = ("/bin", "/sbin", "/lib", "/lib64", "/lib32", "/libx32")
# /etc 안에서 밖을 가리킬 수 있는 네트워크 파일. 대상 파일 하나만 연결한다.
ETC_LINKS = ("/etc/resolv.conf", "/etc/hosts")
# 참여자 안으로 넘기는 변수. 나머지는 --clearenv로 지운다.
PASS_ENV = frozenset({"LANG", "LC_ALL", "LC_CTYPE", "TERM", "NO_COLOR", "TZ",
                      "CLAUDE_CONFIG_DIR", "CODEX_HOME", "CLAUDE_CODE_OAUTH_TOKEN"})
PATH_INSIDE = "/usr/local/bin:/usr/bin:/bin"


class IsolationError(ValueError):
    """격리를 조립하기 전에 거절한 요청. 아무것도 실행하지 않았다."""


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise IsolationError(message)


@dataclass(frozen=True)
class Sandbox:
    """참여자·시도 하나의 경계. 모든 경로는 절대 경로이고, 안에서도 같은 경로로 보인다."""
    work_dir: str                          # 쓰기 가능. 실행 위치(cwd)
    home: str                              # 안에서 보이는 HOME. 빈 tmpfs로 만든다
    read_only: tuple[str, ...] = ()        # 입력 자료, CLI 실행 파일
    read_write: tuple[str, ...] = ()       # 그 CLI의 설정·인증 폴더
    env: Mapping[str, str] = field(default_factory=dict)   # PASS_ENV에 있는 것만 넘어간다


def cli_mounts(adapter_id: str, exe: str, home: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """그 CLI가 도는 데 필요한 경로: (읽기 전용, 쓰기). 실행 파일은 실제 위치로 풀어 연결한다.

    다른 CLI의 설정·인증 폴더는 넣지 않는다. 무엇이 정말 필요한지는 실제 호출(B1·B2)에서 좁힌다.
    """
    real = os.path.realpath(exe)
    existing = lambda paths: tuple(p for p in paths if os.path.lexists(p))  # noqa: E731
    if adapter_id == "claude-code":
        return (real,), existing((os.path.join(home, ".claude"), os.path.join(home, ".claude.json")))
    if adapter_id == "codex":
        # …/releases/<버전>/bin/codex — 옆의 codex-resources(bwrap, rg)까지 버전 폴더째 읽기 전용으로 둔다.
        return (os.path.dirname(os.path.dirname(real)),), existing((os.path.join(home, ".codex"),))
    raise IsolationError(f"no mount profile for {adapter_id!r}")


def _system_mounts() -> list[str]:
    args: list[str] = []
    for path in SYSTEM_READ_ONLY:
        args += ["--ro-bind", path, path]
    for link in MERGED_USR_LINKS:
        if os.path.islink(link):
            args += ["--symlink", os.readlink(link), link]
        elif os.path.isdir(link):
            args += ["--ro-bind", link, link]
    for link in ETC_LINKS:
        target = os.path.realpath(link)
        if os.path.islink(link) and os.path.isfile(target) and not target.startswith(("/etc/", "/usr/")):
            args += ["--ro-bind", target, target]
    return args


def wrap(argv: Sequence[str], box: Sandbox, *, bwrap: str = BWRAP) -> list[str]:
    """argv를 box 안에서 실행하는 bwrap 명령. runner.run(..., pid_namespace=True)로 실행한다."""
    _require(bool(argv) and all(isinstance(a, str) for a in argv), "argv must be a non-empty list of strings")
    paths = (box.work_dir, box.home, *box.read_only, *box.read_write)
    _require(all(PurePosixPath(p).is_absolute() for p in paths), "sandbox paths must be absolute")
    _require(all(os.path.normpath(p) != "/" for p in paths), "the root directory cannot be bound")
    _require(os.path.normpath(box.home) not in {os.path.normpath(p) for p in box.read_write},
             "HOME itself cannot be writable; bind the CLI's own folders instead")
    for path in (box.work_dir, *box.read_only, *box.read_write):
        _require(os.path.lexists(path), f"{path} does not exist")
    exe = os.path.realpath(argv[0])
    _require(any(exe == p or exe.startswith(p.rstrip("/") + "/") for p in (*box.read_only, *SYSTEM_READ_ONLY)),
             "the executable must be inside a read-only mount")

    args = [bwrap, "--unshare-all", "--share-net", "--die-with-parent", "--new-session", "--clearenv"]
    args += _system_mounts()
    args += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--tmpfs", box.home]
    for path in box.read_write:                    # 쓰기 먼저, 그 안의 읽기 전용이 위에 덮이도록
        args += ["--bind", path, path]
    for path in box.read_only:
        args += ["--ro-bind", path, path]
    args += ["--bind", box.work_dir, box.work_dir, "--chdir", box.work_dir]
    env = {k: v for k, v in box.env.items() if k in PASS_ENV}
    env.update(HOME=box.home, PATH=PATH_INSIDE, TMPDIR="/tmp")
    for name in sorted(env):
        args += ["--setenv", name, env[name]]
    return [*args, "--", exe, *argv[1:]]
