"""Explicit metadata refresh, cached for UI reads. Never starts a model turn.

Codex: the user's explicit refresh runs the isolated app-server probe (limits and the account's model list).
Claude: no probe exists; the panel shows the limits the last finished real Claude attempt reported in its
stream (`claude` callable, normally Controller.claude_account_limit). Neither path adds a model call.
"""
from __future__ import annotations

import copy
from pathlib import Path
import threading
import time

from core.quota import claude_limit_projection


class AccountQuota:
    def __init__(self, data_dir: Path, *, enabled: bool, reader=None, clock=time.time, claude=None,
                 codex_model: str | None = None):
        self.enabled = enabled
        self.data_dir, self._reader, self._clock = data_dir, reader, clock
        self._claude, self.codex_model = claude, codex_model
        self._refresh_lock = threading.Lock()
        self._attempted_at = None
        self._snapshot = None
        self._models = None
        self._failed = False

    def view(self) -> dict:
        now = int(self._clock())
        quota = copy.deepcopy(self._snapshot)
        if quota is not None:
            age = now - quota["observed_at"]
            stale = self._failed or age < 0 or age > 120
            quota["freshness"] = "stale" if stale else "fresh"
            for row in quota["limits"]:
                expired = row["resets_at"] is not None and row["resets_at"] <= now
                row["status"] = ("unknown" if row["used_percent"] is None else
                                 "stale" if stale or expired else "observed")
            known = [r for r in quota["limits"] if r["used_percent"] is not None]
            quota["status"] = ("unknown" if not known else
                               "stale" if any(r["status"] == "stale" for r in known) else "observed")
        retry = 0 if self._attempted_at is None else max(0, self._attempted_at + 60 - now)
        claude = None
        if self._claude is not None:
            claude = claude_limit_projection(self._claude(), now=now)
        return {"enabled": self.enabled, "provider": "codex", "inference_requests_sent": 0,
                "refreshing": self._refresh_lock.locked(), "retry_after_seconds": retry,
                "refresh_failed": self._failed, "quota": quota,
                "requested_model": self.codex_model, "models": copy.deepcopy(self._models),
                "claude": {"configured": self._claude is not None, "quota": claude}}

    def refresh(self) -> dict:
        if not self.enabled or not self._refresh_lock.acquire(blocking=False):
            return self.view()
        try:
            now = int(self._clock())
            if self._attempted_at is None or now - self._attempted_at >= 60:
                self._attempted_at = now
                if self._reader is None:
                    from app.codex_account import probe
                    reader = probe
                else:
                    reader = self._reader
                try:
                    report = reader(self.data_dir)
                    quota = report.get("quota") if report.get("tree_confirmed_empty") is True else None
                    self._failed = quota is None
                    if quota is not None:
                        self._snapshot = copy.deepcopy(quota)
                        self._models = copy.deepcopy(report.get("models"))
                except (OSError, ValueError, RuntimeError):
                    self._failed = True  # Never return exception text or erase the last observation.
        finally:
            self._refresh_lock.release()
        return self.view()
