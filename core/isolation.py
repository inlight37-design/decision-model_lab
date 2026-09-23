"""참여자 한 번의 실행을 bubblewrap으로 가둔다(인계 2절 16, W2). Linux·WSL2 전용, 표준 라이브러리만 쓴다.

진입점은 run() 하나다. 조립(plan)과 실행을 묶고, 실행 전에 bubblewrap 실행 파일의 출처를 확인한다. 그래야
PID namespace 추적(자손 전체의 종료 확인)을 이름만 bwrap인 다른 프로그램에 주지 않는다(WSL2 리뷰 WM-03).

보장하려는 것
- 파일: 참여자에게는 명시한 것만 보인다. 시스템 폴더(/usr, /etc와 병합된 /bin·/lib 링크)는 읽기 전용,
  HOME과 /tmp는 빈 tmpfs다. 입력 자료와 CLI 실행 파일은 읽기 전용, 작업 폴더와 그 CLI 자신의 설정·인증
  폴더만 쓰기다. 원장, 다른 참여자의 초안, 지난 합성, 다른 CLI의 인증, /mnt(Windows 드라이브), /run(WSL
  interop와 사용자 버스 소켓)은 연결하지 않는다. /etc 안의 링크가 밖을 가리키면(WSL의 resolv.conf →
  /mnt/wsl/resolv.conf) 그 파일 하나만 연결한다.
- 경로 충돌: 연결할 경로를 실제 경로로 풀어 비교한다. 작업 폴더가 HOME이거나, 읽기 전용 입력과 같거나 그
  안에 있거나(마지막 쓰기 연결이 입력의 그 부분을 쓰기로 연다, A1-04), 다른 연결을 품으면 거절한다. 어떤 연결이
  HOME 자체나 그 위 폴더여도 거절한다. 봉인할 경로(never)는 명시한 연결뿐 아니라 자동 시스템 연결(/usr, /etc,
  병합 링크 폴더, /etc 밖을 가리키는 네트워크 파일)과도 비교한다(WM-04, A1-04). 읽기·쓰기 폴더 안의 읽기 전용
  연결(Codex의 실행 버전 폴더)은 의도한 겹침이다.
- 수명: 별도 PID namespace(--unshare-all에 포함)와 --die-with-parent. namespace의 첫 프로세스(bwrap의
  reaper)가 끝나면 커널이 안의 모든 프로세스를 끝내고, 그 첫 프로세스는 안이 빌 때까지 끝나지 않는다.
  그래서 runner는 bwrap의 프로세스 그룹이 빈 것으로 자손 전체의 종료를 확인한다(runner.PID_NAMESPACE).
- 환경: 허용한 변수만 bwrap 프로세스의 환경으로 넘긴다. 값은 명령 인자에 싣지 않는다 — /proc의 명령줄과
  실행 기록에 남기 때문이다(WM-02). 인증 토큰·과금 변수는 넘기지 않고 거절한다. 인증은 CLI의 로그인 파일을 쓴다.
  자식의 환경은 이 목록과 똑같지 않다 — bwrap이 --chdir에 맞춰 PWD를 더한다(0.9.0 관측, A1 리뷰 질문 2).

보장하지 않는 것
- 네트워크. 모델 API가 필요해 공유한다(--share-net). 같은 네트워크 namespace의 localhost 포트와 abstract
  unix 소켓에는 닿는다 → controller 제어 API는 참여자에게 없는 토큰으로 막는다. 그런 서비스에 요청해 만든
  작업은 namespace의 자손이 아니므로 종료 보장 밖이다.
- 메모리·CPU 상한.
- CLI가 자기 설정·인증 폴더에서 무엇을 읽고 쓰는지. 토큰 갱신에 쓰기가 필요하다.
- 검사와 실행 사이에 파일이 바뀌는 경쟁.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import PurePosixPath
import stat
import sys
import threading
from typing import Mapping, Sequence

from core import runner
from core.env import BILLING_VARS

BWRAP = "/usr/bin/bwrap"
SYSTEM_READ_ONLY = ("/usr", "/etc")
MERGED_USR_LINKS = ("/bin", "/sbin", "/lib", "/lib64", "/lib32", "/libx32")
# /etc 안에서 밖을 가리킬 수 있는 네트워크 파일. 대상 파일 하나만 연결한다.
ETC_LINKS = ("/etc/resolv.conf", "/etc/hosts")
# 참여자 안으로 넘기는 변수. 나머지는 버린다.
PASS_ENV = frozenset({"LANG", "LC_ALL", "LC_CTYPE", "TERM", "NO_COLOR", "TZ", "CLAUDE_CONFIG_DIR", "CODEX_HOME"})
# 격리 안으로 넘기면 안 되는 비밀·과금 변수. 조용히 버리지 않고 거절한다.
REFUSED_ENV = BILLING_VARS | {"CLAUDE_CODE_OAUTH_TOKEN"}
PATH_INSIDE = "/usr/local/bin:/usr/bin:/bin"


class IsolationError(ValueError):
    """격리를 조립하기 전에 거절한 요청. 아무것도 실행하지 않았다."""


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise IsolationError(message)


@dataclass(frozen=True)
class Sandbox:
    """참여자·시도 하나의 경계. 모든 경로는 절대 경로이고, 안에서는 실제 경로로 보인다."""
    work_dir: str                          # 쓰기 가능. 실행 위치(cwd)
    home: str                              # 안에서 보이는 HOME. 빈 tmpfs로 만든다
    read_only: tuple[str, ...] = ()        # 입력 자료, CLI 실행 파일
    read_write: tuple[str, ...] = ()       # 그 CLI의 설정·인증 폴더
    env: Mapping[str, str] = field(default_factory=dict)   # PASS_ENV에 있는 것만 넘어간다
    never: tuple[str, ...] = ()            # 어떤 연결과도 겹치면 안 되는 경로(원장, 봉인 저장소)


def cli_mounts(adapter_id: str, exe: str, home: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """그 CLI가 도는 데 필요한 경로: (읽기 전용, 쓰기). 실행 파일은 실제 위치로 풀어 연결한다.

    다른 CLI의 설정·인증 폴더는 넣지 않는다. 지금은 자기 설정 폴더 전체를 쓰기로 연결한다 — 그 CLI의 지난
    세션 기록도 보인다. 무엇이 정말 필요한지는 실제 호출(B1·B2)에서 좁힌다.
    """
    real = os.path.realpath(exe)
    existing = lambda paths: tuple(p for p in paths if os.path.lexists(p))  # noqa: E731
    if adapter_id == "claude-code":
        return (real,), existing((os.path.join(home, ".claude"), os.path.join(home, ".claude.json")))
    if adapter_id == "codex":
        # …/releases/<버전>/bin/codex — 옆의 codex-resources(bwrap, rg)까지 버전 폴더째 읽기 전용으로 둔다.
        return (os.path.dirname(os.path.dirname(real)),), existing((os.path.join(home, ".codex"),))
    raise IsolationError(f"no mount profile for {adapter_id!r}")


def _within(path: str, parent: str) -> bool:
    """path가 parent이거나 그 아래인가(실제 경로끼리)."""
    return path == parent or path.startswith(parent.rstrip("/") + "/")


def _system_mounts() -> tuple[list[str], list[str]]:
    """시스템 연결의 bwrap 인자와, 그 연결이 참여자에게 보이게 하는 호스트 경로(실제 경로)."""
    args: list[str] = []
    bound: list[str] = []
    for path in SYSTEM_READ_ONLY:
        args += ["--ro-bind", path, path]
        bound.append(os.path.realpath(path))
    for link in MERGED_USR_LINKS:
        if os.path.islink(link):
            args += ["--symlink", os.readlink(link), link]
        elif os.path.isdir(link):
            args += ["--ro-bind", link, link]
            bound.append(os.path.realpath(link))
    for link in ETC_LINKS:
        target = os.path.realpath(link)
        if os.path.islink(link) and os.path.isfile(target) and not target.startswith(("/etc/", "/usr/")):
            args += ["--ro-bind", target, target]
            bound.append(target)
    return args, bound


def plan(argv: Sequence[str], box: Sandbox) -> tuple[list[str], dict[str, str]]:
    """box 안에서 argv를 실행하는 bwrap 명령과, bwrap 프로세스에 줄 환경. 실행은 run()이 한다."""
    _require(bool(argv) and all(isinstance(a, str) for a in argv), "argv must be a non-empty list of strings")
    given = (box.work_dir, box.home, *box.read_only, *box.read_write, *box.never)
    _require(all(PurePosixPath(p).is_absolute() for p in given), "sandbox paths must be absolute")
    refused = sorted(name for name in box.env if name.upper() in REFUSED_ENV)
    _require(not refused, f"credential or billing variables are not passed into a sandbox: {refused}")
    for path in (box.work_dir, *box.read_only, *box.read_write):
        _require(os.path.lexists(path), f"{path} does not exist")

    real = os.path.realpath
    work, home = real(box.work_dir), real(box.home)
    ro, rw, never = ([real(p) for p in group] for group in (box.read_only, box.read_write, box.never))
    mounts = [work, *ro, *rw]
    _require(all(p != "/" for p in mounts + [home]), "the root directory cannot be bound")
    _require(not any(_within(home, p) for p in mounts),
             "HOME itself or a folder above it cannot be bound; bind the CLI's own folders instead")
    _require(work not in ro, "the work folder cannot also be a read-only input")
    _require(not any(_within(work, p) for p in ro),
             "the work folder cannot be inside a read-only input; its writable bind would open that part of the input")
    _require(not any(_within(p, work) for p in ro + rw if p != work),
             "the work folder cannot contain another mount; a later writable bind would cover it")
    system_args, system = _system_mounts()
    _require(not any(_within(p, n) or _within(n, p) for p in mounts + system for n in never),
             "a mount overlaps a path that must stay out of the sandbox")
    exe = real(argv[0])
    _require(any(_within(exe, p) for p in (*ro, *SYSTEM_READ_ONLY)), "the executable must be inside a read-only mount")

    args = [BWRAP, "--unshare-all", "--share-net", "--die-with-parent", "--new-session"]
    args += system_args
    args += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--tmpfs", home]
    for path in rw:                                # 쓰기 먼저, 그 안의 읽기 전용이 위에 덮이도록
        args += ["--bind", path, path]
    for path in ro:
        args += ["--ro-bind", path, path]
    args += ["--bind", work, work, "--chdir", work, "--", exe, *argv[1:]]
    child_env = {k: v for k, v in box.env.items() if k in PASS_ENV}
    child_env.update(HOME=home, PATH=PATH_INSIDE, TMPDIR="/tmp")
    return args, child_env


def _trusted_bwrap() -> None:
    """bwrap 실행 파일을 시스템이 설치한 것으로 볼 만한가: 정해진 경로, 일반 파일, root 소유, 그룹·다른 사용자가
    못 쓴다. 패키지 서명이나 해시는 확인하지 않는다 — 이름만 bwrap인 사용자 파일을 거절하는 데까지다."""
    _require(sys.platform == "linux", "isolation runs on Linux and WSL2 only")
    try:
        info = os.stat(BWRAP)
    except OSError:
        raise IsolationError(f"{BWRAP} is not installed") from None
    _require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & (stat.S_IWGRP | stat.S_IWOTH),
             f"{BWRAP} is not a root-owned, non-writable system binary")


def run(argv: Sequence[str], box: Sandbox, *, timeout: float, stdin_text: str | None = None,
        max_output_bytes: int = runner.DEFAULT_MAX_OUTPUT,
        cancel: threading.Event | None = None) -> runner.RunResult:
    """argv를 box 안에서 한 번 실행한다. 결과의 containment는 runner.PID_NAMESPACE다."""
    args, child_env = plan(argv, box)
    _trusted_bwrap()
    return runner._execute(runner.validate_argv(args), cwd=os.path.realpath(box.work_dir), env=child_env,
                           timeout=timeout, stdin_text=stdin_text, max_output_bytes=max_output_bytes,
                           cancel=cancel, pid_namespace=True)
