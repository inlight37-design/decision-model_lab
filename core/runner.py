"""native CLI 한 번을 셸 없이 실행하고, 끝났는지 확인한 만큼만 말한다.

무엇을 실행할지는 호출자가 argv로 정한다(adapters.py가 조립·검증한다). 이 모듈은
인증·과금·권한이 옳은지 판단하지 않는다. 지키는 계약(PR #4 R06, Hermes 조사 HP-01):

- 실행 파일은 절대 경로다. 셸을 거치지 않고, .bat/.cmd는 거절한다(Windows는 그런 파일을
  cmd.exe로 돌려 인자를 다시 해석한다).
- stdin은 입력을 쓴 뒤 닫는다. 입력이 없으면 처음부터 닫는다. codex exec는 열린 stdin을
  추가 입력으로 기다린다(aux-pc P1). 입력은 CLI를 띄우기 전에 인코딩하고, 다 썼는지를
  input_delivery로 남긴다(WSL2 리뷰 WM-01).
- stdout과 stderr를 따로 받고, 상한을 넘으면 자르고 표시한다.
- 제한 시간이 지나면 프로세스 트리를 끝낸다. 답 텍스트가 있어도 timed_out이다(HF-06).
  Hermes의 codex 경로는 이 경우 텍스트를 완료로 받아들인다 — 옮기지 않는다.
- 추적 단위가 비었는지 확인하지 못하면 unknown이다. 예산을 돌려받지 않는다(HF-07).
- exit 0은 프로세스가 끝났다는 뜻이지 작업이 성공했다는 뜻이 아니다.
- 프로세스를 만든 뒤의 명시적 정리 대기에는 상한(CLEANUP_LIMIT)이 있다(경계 리뷰 R02). 운영체제의
  프로세스 생성 지연까지 포함한 벽시계 보장은 아니다. 돌아온 뒤에도 파이프를 쥔 프로세스가 남으면
  입출력 스레드가 남는다 — lingering()이 센다(WSL2 리뷰 WM-07).

추적 단위(containment): Windows는 job object(ctypes) — 자손이 떠날 수 없다. 그 밖은 새
session의 프로세스 그룹 — setsid 등으로 새 세션을 만든 자손은 보이지 않는다. 그래서 결과는
두 가지를 따로 말한다(경계 리뷰 R01). unit_confirmed_empty는 추적 단위가 비었는지,
tree_confirmed_empty는 자손 전체가 끝났는지다. 프로세스 그룹만으로는 뒤쪽을 확인할 수 없어
None이다. 자원 해제·예산 반환은 tree_confirmed_empty가 True일 때만 한다. Linux에서 이것을
True로 만드는 것은 core.isolation.run()뿐이다 — 출처를 확인한 bubblewrap으로 실행해 PID namespace를
추적 단위로 쓴다. 일반 run()에는 namespace 보장을 붙이지 않는다(WSL2 리뷰 WM-03).
Windows에서 job 배정에 실패하면 트리 확인을 하지 않고 unknown 쪽으로 기운다.
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
EXITED = "exited"                    # 스스로 끝났고 추적 단위가 빈 것을 확인했다
TIMED_OUT = "timed_out"              # 제한 시간에 끊었고 추적 단위가 빈 것을 확인했다
CANCELLED = "cancelled"              # 취소 요청으로 끊었고 추적 단위가 빈 것을 확인했다
UNKNOWN = "unknown"                  # 끝났는지 확인하지 못했다. 예산 점유를 유지한다
FAILED_TO_START = "failed_to_start"  # 프로세스를 만들지 못했다. 모델 호출은 없었다
STATES = (EXITED, TIMED_OUT, CANCELLED, UNKNOWN, FAILED_TO_START)

# 추적 단위. 자손 전체를 담는 단위만 WHOLE_TREE에 넣는다.
JOB_OBJECT = "job_object"            # Windows. 브레이크어웨이를 허용하지 않으므로 자손이 떠날 수 없다
PROCESS_GROUP = "process_group"      # POSIX. 새 세션을 만든 자손은 담지 못한다
# POSIX + core.isolation의 bwrap. 자손은 PID namespace를 떠날 수 없고, namespace의 첫 프로세스(bwrap
# 프로세스 그룹 안)는 안이 빌 때까지 끝나지 않는다. 그래서 그룹이 비면 자손 전체가 끝난 것이다.
PID_NAMESPACE = "pid_namespace"
WHOLE_TREE = frozenset({JOB_OBJECT, PID_NAMESPACE})

DEFAULT_MAX_OUTPUT = 8 * 1024 * 1024
_CHUNK = 64 * 1024
_GRACE = 3.0          # 종료 요청 뒤 기다리는 시간(초)
_DRAIN = 1.0          # 스스로 끝난 뒤 곁가지 프로세스가 따라 끝나기를 기다리는 시간(초)
_KILL = 1.0           # SIGKILL 뒤 기다리는 시간(초)
_CONFIRM = 2.0        # 끝낸 뒤 추적 단위가 비기를 기다리는 시간(초)
_POLL = 0.05
# timeout 뒤 정리 단계가 쓰는 시간의 상한(초): 곁가지 대기, 종료 요청과 강제 종료, 회수, 비었는지
# 확인, 출력 스레드 합류를 모두 더한 값이다. 이보다 오래 걸리게 하는 대기는 두지 않는다.
CLEANUP_LIMIT = _DRAIN + (_GRACE + _KILL) + _GRACE + _CONFIRM + _GRACE


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
    # 끝낼 때 추적 단위(containment)가 빈 것을 확인했는가. None이면 확인 수단이 없었다.
    unit_confirmed_empty: bool | None
    error: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    containment: str | None = None   # JOB_OBJECT | PROCESS_GROUP | PID_NAMESPACE | None(추적하지 못했다)
    # stdin 입력의 전달 상태: INPUT_COMPLETE | INPUT_FAILED | INPUT_INCOMPLETE | None(입력 없음).
    # 프로세스 상태(state)와 따로 둔다. 전달이 완전하지 않으면 adapters.interpret()가 답을 받지 않는다.
    input_delivery: str | None = None

    @property
    def tree_confirmed_empty(self) -> bool | None:
        """자손 전체가 끝났음을 확인했는가. 추적 단위가 자손 전체를 담지 못하면 None이다."""
        if self.state == FAILED_TO_START:
            return True
        if self.unit_confirmed_empty is not True:
            return self.unit_confirmed_empty
        return True if self.containment in WHOLE_TREE else None


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
    """한 스트림을 끝까지 읽되 상한까지만 보관한다. 넘친 뒤에도 파이프는 비운다.

    스트림은 이 스레드가 끝날 때 스스로 닫는다. 읽는 중인 buffered stream을 다른 스레드에서
    닫으면 읽기가 끝날 때까지 close()가 막힌다 — 파이프를 쥔 자손이 남으면 run()이 돌아오지
    않았다(경계 리뷰 R02).
    """

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
        finally:
            try:
                self.stream.close()
            except OSError:
                pass

    def text(self) -> str:
        return b"".join(self.chunks).decode("utf-8", errors="replace").replace("\r\n", "\n")


class _Writer(threading.Thread):
    """stdin에 입력을 쓰고 닫는다. 몇 바이트를 썼는지, 왜 멈췄는지를 남긴다(WSL2 리뷰 WM-01).

    CLI가 입력을 다 읽기 전에 stdin을 닫으면 쓰기가 실패한다. 그 사실을 버리면 질문의 일부만 받은
    답이 정상 답처럼 보인다. 파이프에 다 썼다는 것이 CLI가 다 썼다는 증거는 아니다.
    """

    def __init__(self, stream, data: bytes) -> None:
        super().__init__(daemon=True)
        self.stream, self.data = stream, data
        self.written = 0
        self.error: str | None = None

    def run(self) -> None:
        try:
            fd = self.stream.fileno()
            view = memoryview(self.data)
            while self.written < len(view):
                self.written += os.write(fd, view[self.written:self.written + _CHUNK])
        except OSError as exc:
            self.error = type(exc).__name__
        finally:
            try:
                self.stream.close()
            except OSError as exc:
                self.error = self.error or type(exc).__name__


# 입력 전달 상태. None은 stdin 입력이 없었다는 뜻이다.
INPUT_COMPLETE = "complete"      # 파이프에 다 쓰고 닫았다
INPUT_FAILED = "failed"          # 다 쓰기 전에 쓰기가 실패했다(CLI가 stdin을 먼저 닫는 등)
INPUT_INCOMPLETE = "incomplete"  # 돌아올 때까지 쓰기가 끝나지 않았다

_LINGERING: set[threading.Thread] = set()


def lingering() -> int:
    """돌아온 뒤에도 끝나지 않은 입출력 스레드 수(WM-07). 각각 파이프 fd 하나를 쥔다.

    추적 단위 밖에서 파이프를 쥔 프로세스가 끝나야 사라진다. controller는 이 수와 `unknown` 결과로
    정리되지 않은 시도를 세고, 상한을 넘으면 새 시도를 멈춘다.
    """
    for thread in [t for t in _LINGERING if not t.is_alive()]:
        _LINGERING.discard(thread)
    return len(_LINGERING)


class _Tree:
    """자식 프로세스까지 포함한 트리. 플랫폼별로 끝내기와 비었는지 세기만 한다."""

    def __init__(self, proc: subprocess.Popen, *, pid_namespace: bool = False) -> None:
        self.proc = proc
        self.job = None
        self.note: str | None = None
        self.containment: str | None = None if IS_WINDOWS else (PID_NAMESPACE if pid_namespace else PROCESS_GROUP)
        if IS_WINDOWS:
            try:
                self.job = _WindowsJob()
                if not self.job.assign(proc.pid):
                    self.note = "job object assignment failed; tree is not tracked"
                    self.job.close()
                    self.job = None
                else:
                    self.containment = JOB_OBJECT
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
                try:
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, check=False, timeout=_GRACE + _KILL)
                except subprocess.TimeoutExpired:
                    pass
            return
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(self.proc.pid, sig)
            except ProcessLookupError:
                return
            deadline = time.monotonic() + (_GRACE if sig == signal.SIGTERM else _KILL)
            while time.monotonic() < deadline:
                if self.proc.poll() is not None and self.active() == 0:
                    return
                time.sleep(_POLL)

    def confirm_empty(self, wait: float = _CONFIRM) -> bool | None:
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


def _check_pid_namespace(args: tuple[str, ...]) -> None:
    """PID namespace 추적은 core.isolation.run()만 쓴다. 그 함수가 bwrap 실행 파일의 출처를 먼저 확인한다.
    여기서는 명령 모양만 한 번 더 본다 — 이것만으로는 보장이 아니다(WSL2 리뷰 WM-03)."""
    if IS_WINDOWS:
        raise RunnerError("pid_namespace containment is POSIX-only")
    head = args[:args.index("--")] if "--" in args else args
    if (Path(args[0]).name != "bwrap" or "--die-with-parent" not in head
            or not {"--unshare-all", "--unshare-pid"} & set(head)):
        raise RunnerError("pid_namespace needs a bwrap command with a new pid namespace and --die-with-parent")


def run(argv: Sequence[str], *, cwd: str | os.PathLike, env: Mapping[str, str],
        timeout: float, stdin_text: str | None = None,
        max_output_bytes: int = DEFAULT_MAX_OUTPUT,
        cancel: threading.Event | None = None) -> RunResult:
    """한 번 실행한다. 예외 대신 RunResult로 돌려준다(실행 전 검증 실패만 RunnerError).

    격리해서 실행하려면 core.isolation.run()을 쓴다. 자손 전체의 종료를 PID namespace로 확인하는 것은
    그 경로뿐이다.
    """
    return _execute(validate_argv(argv), cwd=cwd, env=env, timeout=timeout, stdin_text=stdin_text,
                    max_output_bytes=max_output_bytes, cancel=cancel, pid_namespace=False)


def _execute(args: tuple[str, ...], *, cwd: str | os.PathLike, env: Mapping[str, str], timeout: float,
             stdin_text: str | None, max_output_bytes: int, cancel: threading.Event | None,
             pid_namespace: bool) -> RunResult:
    if pid_namespace:
        _check_pid_namespace(args)
    try:
        data = stdin_text.encode("utf-8") if stdin_text is not None else None
    except UnicodeEncodeError as exc:  # CLI를 띄우기 전에 거절한다
        raise RunnerError(f"stdin_text cannot be encoded as UTF-8 ({exc.reason})") from None
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
            stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    except OSError as exc:
        return RunResult(args, FAILED_TO_START, None, "", "", False, False,
                         int((time.monotonic() - started) * 1000), None, True,
                         error=type(exc).__name__)  # 아무것도 시작하지 않았으니 비어 있다

    tree = _Tree(proc, pid_namespace=pid_namespace)
    notes = [tree.note] if tree.note else []
    out, err = _Reader(proc.stdout, max_output_bytes), _Reader(proc.stderr, max_output_bytes)
    out.start()
    err.start()
    writer = _Writer(proc.stdin, data) if data is not None else None
    if writer:
        writer.start()

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
    joined_by = time.monotonic() + _GRACE
    for reader in (out, err):
        reader.join(timeout=max(0.0, joined_by - time.monotonic()))
        if reader.is_alive():
            # 추적 단위 밖에서 파이프를 쥔 프로세스가 아직 있다는 뜻이다. 스트림은 닫지 않고 둔다 —
            # 닫으면 그 프로세스가 끝날 때까지 여기서 막힌다. 읽는 스레드가 EOF에서 닫는다.
            notes.append("an output pipe stayed open after termination")
            confirmed = False
            _LINGERING.add(reader)
    delivery = None
    if writer:
        writer.join(timeout=max(0.0, joined_by - time.monotonic()))
        if writer.is_alive():
            delivery = INPUT_INCOMPLETE
            _LINGERING.add(writer)
        else:
            delivery = INPUT_COMPLETE if writer.error is None and writer.written == len(data) else INPUT_FAILED
        if delivery != INPUT_COMPLETE:
            notes.append(f"stdin {delivery}: wrote {writer.written} of {len(data)} bytes"
                         + (f" ({writer.error})" if writer.error else ""))

    if confirmed is True and proc.poll() is not None:
        state = reason or EXITED
    else:
        state = UNKNOWN
        if confirmed is None:
            notes.append("process tree could not be counted on this platform")
    return RunResult(args, state, proc.poll(), out.text(), err.text(), out.truncated, err.truncated,
                     int((time.monotonic() - started) * 1000), leftover, confirmed,
                     notes=tuple(notes), containment=tree.containment, input_delivery=delivery)


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
