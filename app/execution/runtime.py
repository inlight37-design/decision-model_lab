"""One in-process owner of the ledger, configuration, lock and live worker handles.

Database records remain authoritative. Worker presence is never termination proof.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import threading
from app.store import Store
from app.execution.executor import Executor


@dataclass
class Runtime:
    store: Store
    executor: Executor
    max_parallel: int
    unsettled_limit: int
    timeout: float
    work_root: str
    max_real_calls: int | None
    provider_call_caps: dict
    lock: object = field(default_factory=threading.RLock)
    closing: bool = False
    paused: bool = False
    workers: dict[str, tuple[threading.Thread, threading.Event]] = field(default_factory=dict)
    syntheses: dict[str, tuple[threading.Thread, threading.Event, str]] = field(default_factory=dict)
    upper_workers: dict[str, tuple[threading.Thread, threading.Event]] = field(default_factory=dict)
