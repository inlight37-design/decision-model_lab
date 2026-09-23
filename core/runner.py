"""native CLI 한 번을 셸 없이 실행하고, 끝났는지 확인한 만큼만 말한다.

무엇을 실행할지는 호출자가 argv로 정한다(adapters.py가 조립·검증한다). 이 모듈은
인증·과금·권한이 옳은지 판단하지 않는다. 지키는 계약(PR #4 R06, Hermes 조사 HP-01):

- 실행 파일은 절대 경로다. 셸을 거치지 않고, .bat/.cmd는 거절한다(Windows는 그런 파일을
  cmd.exe로 돌려 인자를 다시 해석한다).
- stdin은 입력을 쓴 뒤 닫는다. 입력이 없으면 처음부터 닫는다. codex exec는 열린 stdin을
  추가 입력으로 기다린다(aux-pc P1).
- stdout과 stderr를 따로 받고, 상한을 넘으면 자르고 표시한다.
- 제한 시간이 지나면 프로세스 트리를 끝낸다. 답 텍스트가 있어도 timed_out이다(HF-06).
  Hermes의 codex 경로는 이 경우 텍스트를 완료로 받아들인다 — 옮기지 않는다.
- 트리가 비었는지 확인하지 못하면 unknown이다. 예산을 돌려받지 않는다(HF-07).
- exit 0은 프로세스가 끝났다는 뜻이지 작업이 성공했다는 뜻이 아니다.

트리 추적: Windows는 job object(ctypes), 그 밖은 새 session의 프로세스 그룹. 자기 그룹을
떠난 프로세스(setsid 등)는 POSIX에서 추적하지 못한다. Windows에서 job 배정에 실패하면
트리 확인을 하지 않고 unknown 쪽으로 기운다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
from typing import Mapping, Sequence

IS_WINDOWS = os.name == "nt"

# 프로세스 상태. 의미상 성공 여부는 adapters.interpret()가 따로 정한다.
EXITED = "exited"                    # 스스로 끝났고 트리가 빈 것을 확인했다
TIMED_OUT = "timed_out"              # 제한 시간에 끊었고 트리가 빈 것을 확인했다
CANCELLED = "cancelled"              # 취소 요청으로 끊었고 트리가 빈 것을 확인했다
UNKNOWN = "unknown"                  # 끝났는지 확인하지 못했다. 예산 점유를 유지한다
FAILED_TO_START = "failed_to_start"  # 프로세스를 만들지 못했다. 모델 호출은 없었다
STATES = (EXITED, TIMED_OUT, CANCELLED, UNKNOWN, FAILED_TO_START)

DEFAULT_MAX_OUTPUT = 8 * 1024 * 1024
_CHUNK = 64 * 1024
_GRACE = 3.0          # 종료 요청 뒤 기다리는 시간(초)
_DRAIN = 1.0          # 스스로 끝난 뒤 곁가지 프로세스가 따라 끝나기를 기다리는 시간(초)
_POLL = 0.05


class RunnerError(ValueError):
    """실행 전에 거절한 요청. 모델 호출은 일어나지 않았다."""


@dataclass(frozen=True)
class RunResult:
    argv: tuple[str, ...]
    state: str
    exit_code: int | None
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    duration_ms: int
    # 원래 프로세스가 끝난 뒤에도 남아 있던 자식 수. None이면 셀 수 없었다.
    leftover_processes: int | None
    # 끝낼 때 트리가 빈 것을 확인했는가. None이면 확인 수단이 없었다.
    tree_confirmed_empty: bool | None
    error: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


def validate_argv(argv: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(argv, (list, tuple)) or not argv or not all(isinstance(a, str) for a in argv):
        raise RunnerError("argv must be a non-empty list of strings")
    exe = argv[0]
    if not os.path.isabs(exe):
        raise RunnerError("argv[0] must be an absolute path; resolve it before running")
    if Path(exe).suffix.lower() in (".bat", ".cmd"):
        raise RunnerError("batch files run through cmd.exe and are refused")
    if any("\x00" in a for a in argv):
        raise RunnerError("argv contains a NUL character")
    return tuple(argv)


class _Reader(threading.Thread):
    """한 스트림을 끝까지 읽되 상한까지만 보관한다. 넘친 뒤에도 파이프는 비운다."""

    def __init__(self, stream, limit: int) -> None:
        super().__init__(daemon=True)
        self.stream, self.limit = stream, limit
        self.chunks: list[bytes] = []
        self.size = 0
        self.truncated = False

    def run(self) -> None:
        try:
            while True:
                chunk = self.stream.read1(_CHUNK) if hasattr(self.stream, "read1") else self.stream.read(_CHUNK)
                if not chunk:
                    return
                room = self.limit - self.size
                if room > 0:
                    self.chunks.append(chunk[:room])
                    self.size += min(len(chunk), room)
                if len(chunk) > max(room, 0):
                    self.truncated = True
        except (OSError, ValueError):
            return

    def text(self) -> str:
        return b"".join(self.chunks).decode("utf-8", errors="replace").replace("\r\n", "\n")


def _write_stdin(stream, data: bytes) -> None:
    try:
        if data:
            stream.write(data)
    except (BrokenPipeError, OSError):
        pass
    finally:
        try:
            stream.close()
        except OSError:
            pass


class _Tree:
    """자식 프로세스까지 포함한 트리. 플랫폼별로 끝내기와 비었는지 세기만 한다."""

    def __init__(self, proc: subprocess.Popen) -> None:
        self.proc = proc
        self.job = None
        self.note: str | None = None
        if IS_WINDOWS:
            try:
                self.job = _WindowsJob()
                if not self.job.assign(proc.pid):
                    self.note = "job object assignment failed; tree is not tracked"
                    self.job.close()
                    self.job = None
            except OSError as exc:
                self.note = f"job object unavailable ({exc}); tree is not tracked"
                self.job = None

    def active(self) -> int | None:
        """트리에 살아 있는 프로세스 수. 원래 프로세스가 끝난 뒤에 부르면 남은 자식 수다."""
        if IS_WINDOWS:
            return self.job.active_processes() if self.job else None
        try:
            os.killpg(self.proc.pid, 0)
        except ProcessLookupError:
            return 0
        except PermissionError:
            return None
        return 1  # 그룹에 무언가 남아 있다. 정확한 수는 표준 라이브러리로 셀 수 없다

    def kill(self) -> None:
        if IS_WINDOWS:
            if self.job:
                self.job.terminate()
            else:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, check=False)
            return
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(self.proc.pid, sig)
            except ProcessLookupError:
                return
            deadline = time.monotonic() + (_GRACE if sig == signal.SIGTERM else 1.0)
            while time.monotonic() < deadline:
                if self.proc.poll() is not None and self.active() == 0:
                    return
                time.sleep(_POLL)

    def confirm_empty(self, wait: float = 2.0) -> bool | None:
        deadline = time.monotonic() + wait
        while True:
            count = self.active()
            if count == 0:
                return True
            if count is None:
                return None
            if time.monotonic() >= deadline:
                return False
            time.sleep(_POLL)

    def close(self) -> None:
        if self.job:
            self.job.close()  # KILL_ON_JOB_CLOSE: 여기까지 남은 것은 함께 끝난다
            self.job = None


def run(argv: Sequence[str], *, cwd: str | os.PathLike, env: Mapping[str, str],
        timeout: float, stdin_text: str | None = None,
        max_output_bytes: int = DEFAULT_MAX_OUTPUT,
        cancel: threading.Event | None = None) -> RunResult:
    """한 번 실행한다. 예외 대신 RunResult로 돌려준다(실행 전 검증 실패만 RunnerError)."""
    args = validate_argv(argv)
    if not (isinstance(timeout, (int, float)) and timeout > 0):
        raise RunnerError("timeout must be a positive number of seconds")
    if not (isinstance(max_output_bytes, int) and max_output_bytes > 0):
        raise RunnerError("max_output_bytes must be a positive integer")
    if not Path(cwd).is_dir():
        raise RunnerError("cwd must be an existing directory")
    started = time.monotonic()
    kwargs: dict = {}
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen(
            list(args), cwd=str(cwd), env=dict(env), shell=False,
            stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    except OSError as exc:
        return RunResult(args, FAILED_TO_START, None, "", "", False, False,
                         int((time.monotonic() - started) * 1000), None, True,
                         error=type(exc).__name__)

    tree = _Tree(proc)
    notes = [tree.note] if tree.note else []
    out, err = _Reader(proc.stdout, max_output_bytes), _Reader(proc.stderr, max_output_bytes)
    out.start()
    err.start()
    if stdin_text is not None:
        threading.Thread(target=_write_stdin, args=(proc.stdin, stdin_text.encode("utf-8")),
                         daemon=True).start()

    deadline = started + timeout
    reason = None
    while proc.poll() is None:
        if cancel is not None and cancel.is_set():
            reason = CANCELLED
            break
        if time.monotonic() >= deadline:
            reason = TIMED_OUT
            break
        try:
            proc.wait(timeout=_POLL)
        except subprocess.TimeoutExpired:
            pass

    leftover = None
    if reason is None:
        # 원래 프로세스는 스스로 끝났다. Windows의 conhost처럼 곧 따라 끝나는 것은 잠깐
        # 기다리고, 그래도 남은 자식은 세어 기록한 뒤 트리째 끝낸다.
        leftover = 0 if tree.confirm_empty(wait=_DRAIN) else tree.active()
        if leftover:
            notes.append(f"{leftover} process(es) outlived the CLI and were terminated")
            tree.kill()
    else:
        tree.kill()
    try:
        proc.wait(timeout=_GRACE)
    except subprocess.TimeoutExpired:
        pass
    confirmed = tree.confirm_empty() if proc.poll() is not None else False
    tree.close()
    for reader in (out, err):
        reader.join(timeout=_GRACE)
        if reader.is_alive():
            # 파이프를 쥔 프로세스가 아직 있다는 뜻이다.
            notes.append("an output pipe stayed open after termination")
            confirmed = False
    for stream in (proc.stdout, proc.stderr):
        try:
            stream.close()
        except OSError:
            pass

    if confirmed is True and proc.poll() is not None:
        state = reason or EXITED
    else:
        state = UNKNOWN
        if confirmed is None:
            notes.append("process tree could not be counted on this platform")
    return RunResult(args, state, proc.poll(), out.text(), err.text(), out.truncated, err.truncated,
                     int((time.monotonic() - started) * 1000), leftover, confirmed,
                     notes=tuple(notes))


if IS_WINDOWS:  # pragma: no cover - Windows 전용, 로컬 Windows에서 시험한다
    import ctypes
    from ctypes import wintypes

    class _BasicLimit(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class _IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class _ExtendedLimit(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", _BasicLimit), ("IoInfo", _IoCounters),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    class _Accounting(ctypes.Structure):
        _fields_ = [("TotalUserTime", ctypes.c_int64), ("TotalKernelTime", ctypes.c_int64),
                    ("ThisPeriodTotalUserTime", ctypes.c_int64), ("ThisPeriodTotalKernelTime", ctypes.c_int64),
                    ("TotalPageFaultCount", wintypes.DWORD), ("TotalProcesses", wintypes.DWORD),
                    ("ActiveProcesses", wintypes.DWORD), ("TotalTerminatedProcesses", wintypes.DWORD)]

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    _k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    _k32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID,
                                               wintypes.DWORD, wintypes.LPVOID]
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]

    _KILL_ON_JOB_CLOSE = 0x2000
    _EXTENDED_LIMIT_CLASS = 9
    _ACCOUNTING_CLASS = 1
    _PROCESS_SET_QUOTA, _PROCESS_TERMINATE = 0x0100, 0x0001

    class _WindowsJob:
        def __init__(self) -> None:
            self.handle = _k32.CreateJobObjectW(None, None)
            if not self.handle:
                raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
            info = _ExtendedLimit()
            info.BasicLimitInformation.LimitFlags = _KILL_ON_JOB_CLOSE
            if not _k32.SetInformationJobObject(self.handle, _EXTENDED_LIMIT_CLASS,
                                                ctypes.byref(info), ctypes.sizeof(info)):
                error = ctypes.get_last_error()
                self.close()
                raise OSError(error, "SetInformationJobObject failed")

        def assign(self, pid: int) -> bool:
            process = _k32.OpenProcess(_PROCESS_SET_QUOTA | _PROCESS_TERMINATE, False, pid)
            if not process:
                return False
            try:
                return bool(_k32.AssignProcessToJobObject(self.handle, process))
            finally:
                _k32.CloseHandle(process)

        def active_processes(self) -> int | None:
            info = _Accounting()
            if not _k32.QueryInformationJobObject(self.handle, _ACCOUNTING_CLASS, ctypes.byref(info),
                                                  ctypes.sizeof(info), None):
                return None
            return int(info.ActiveProcesses)

        def terminate(self) -> None:
            _k32.TerminateJobObject(self.handle, 1)

        def close(self) -> None:
            if self.handle:
                _k32.CloseHandle(self.handle)
                self.handle = None
