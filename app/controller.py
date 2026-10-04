"""Application composition and compatibility API. See app/ARCHITECTURE.md.

Existing controller imports remain supported; execution and public data are owned by separate services.
"""
from __future__ import annotations

import os
import tempfile
import time
import uuid
from typing import Any
from app.store import Store
from app.state import (CLI, MANUAL, QUEUED, RUNNING, AWAITING_USER, ACCEPTED, REJECTED, UNKNOWN, NOT_STARTED,
                       INDEPENDENT_ONLY, INCLUDE_UNVERIFIED, QUORUM_POLICIES, ISOLATED, GENERAL, COLLECTED,
                       NO_QUORUM, RunGate, gate, confirmed, synthesis_attempts)
from core import runner
from app.domain import (ParticipantSpec, ControllerError, _CapReached, storable, _storable_meta,
                        acceptance, packet, _marker_echo, MAX_MEMO_CHARS)
from app.context.inputs import (_checked_sources, _bundle_digest, _source_footer, PROMPT, PROMPT_SOURCES,
                                GENERAL_PROMPT, MAX_TASK_CHARS, MAX_SOURCES, MAX_SOURCE_BYTES, MAX_SOURCES_TOTAL,
                                SOURCE_KIND_ORIGINAL, SOURCE_RANGE_WHOLE)
from app.queries.public import SEALED_VIEW_KEYS, CONTAMINATION, NOT_RUN, UNRECORDED
from app.execution.seats import _Seat, SEATS, REFINE_SEAT, NEXT_SEAT, SPLIT_SEAT, COLLATE_SEAT, REVIEW_SEAT
from app.execution.executor import Executor, MockExecutor, _check, _not_started, _bwrap_trusted

from app.execution.runtime import Runtime
from app.repository import RunRepository
from app.execution.invocations import InvocationLedger
from app.context.inputs import InputBuilder
from app.queries.public import PublicQueries
from app.execution.coordinator import ExecutionCoordinator
from app.application.planning import PlanningService
from app.application.reviews import ReviewService
from app.application.synthesis import SynthesisService
from app.application.work import WorkService
from app.application.templates import TemplateService


class Controller:
    """Compatibility entry point and composition root; services own application behavior."""

    def search(self, query, *, task_id=None, kind=None, limit=30):
        return self.queries.search(query, task_id=task_id, kind=kind, limit=limit)

    def activity(self, run_id):
        return self.queries.activity(run_id)

    def memory_sources(self, run_id):
        return self.queries.memory_sources(run_id)

    def __init__(self, store: Store, executor: Executor, *, max_parallel: int = 2, unsettled_limit: int = 2,
                 timeout: float = 60.0, work_root: str | None = None,
                 max_real_calls: int | None = None, provider_call_caps: dict[str, int] | None = None) -> None:
        cap, providers = store.bind_call_budget(max_real_calls, provider_call_caps)
        self.runtime = Runtime(store, executor, max_parallel, unsettled_limit, timeout,
                               work_root or os.path.join(tempfile.gettempdir(), "dml-work"), cap, providers)
        self.repository = RunRepository(self.runtime)
        self.invocations = InvocationLedger(self.runtime)
        self.inputs = InputBuilder(self.runtime, self.repository)
        self.queries = PublicQueries(self.runtime, self.invocations, self.repository)
        self.execution = ExecutionCoordinator(self.runtime, self.inputs, self.invocations, self.repository)
        self.planning = PlanningService(self.runtime, self.execution, self.inputs, self.invocations, self.queries, self.repository)
        self.reviews = ReviewService(self.runtime, self.execution, self.inputs, self.invocations, self.repository)
        self.synthesis = SynthesisService(self.runtime, self.execution, self.inputs, self.invocations, self.queries, self.repository)
        self.work = WorkService(self.runtime, self.execution, self.inputs, self.invocations)
        self.templates = TemplateService(self.runtime, self.inputs)
        self.execution.advance_reviews = self.reviews._advance_reviews
        self.execution._recover()
        with self.runtime.lock:
            self.reviews._advance_reviews(start=False)
        self.runtime.paused = store.row("SELECT COUNT(*) AS n FROM participants JOIN runs USING (run_id) "
                                        "WHERE state = ? AND NOT cancel_requested", QUEUED)["n"] > 0 or bool(
            store.row("SELECT 1 FROM reviews WHERE state = ?", QUEUED))

    def prepare_run(self, question: str, participants: list[ParticipantSpec], *, min_independent: int,
                    quorum_policy: str = INDEPENDENT_ONLY, sources=None, task_id=None, task_title=None,
                    role_board=None, roster=None, run_id=None, assignments=None, refinement=None,
                    proposal=None, split=None, checked=None, use_memory=True) -> dict[str, Any]:
        return self.inputs.prepare_run(question, participants, min_independent=min_independent, quorum_policy=quorum_policy, sources=sources, task_id=task_id, task_title=task_title, role_board=role_board, roster=roster, run_id=run_id, assignments=assignments, refinement=refinement, proposal=proposal, split=split, checked=checked, use_memory=use_memory)

    def create_run(self, question: str, participants: list[ParticipantSpec], *, min_independent: int,
                   quorum_policy: str = INDEPENDENT_ONLY, sources=None, task_id=None, task_title=None,
                   role_board=None, roster=None, run_id=None, confirmation=None, assignments=None,
                   refinement=None, proposal=None, split=None, use_memory=True) -> str:
        return self.work.create_run(question, participants, min_independent=min_independent, quorum_policy=quorum_policy, sources=sources, task_id=task_id, task_title=task_title, role_board=role_board, roster=roster, run_id=run_id, confirmation=confirmation, assignments=assignments, refinement=refinement, proposal=proposal, split=split, use_memory=use_memory)

    def _source_root(self, run_id: str) -> str:
        return self.inputs._source_root(run_id)

    def sources(self, run_id: str) -> list[dict[str, Any]]:
        return self.repository.sources(run_id)

    def _assignment(self, run_id: str, pid: str):
        return self.inputs._assignment(run_id, pid)

    def _member_source_dir(self, run_id: str, pid: str) -> str | None:
        return self.inputs._member_source_dir(run_id, pid)

    def _attempt_input(self, run_id: str, pid: str) -> tuple[str, str | None]:
        return self.inputs._attempt_input(run_id, pid)

    def _synthesis_attempts(self, run_id: str | None = None) -> dict:
        return self.invocations._synthesis_attempts(run_id)

    def _slots_used(self, attempts: dict | None = None) -> int:
        return self.invocations._slots_used(attempts)

    def unsettled(self, attempts: dict | None = None) -> int:
        return self.invocations.unsettled(attempts)

    def call_budget(self, adapter_id: str | None = None) -> dict[str, int | None]:
        return self.invocations.call_budget(adapter_id)

    def claude_account_limit(self) -> dict[str, Any] | None:
        return self.queries.claude_account_limit()

    def pump(self) -> None:
        return self.execution.pump()

    def resume(self) -> None:
        return self.execution.resume()

    def _maybe_reveal(self, run_id: str, tx) -> None:
        return self.execution._maybe_reveal(run_id, tx)

    def cancel_run(self, run_id: str) -> None:
        return self.execution.cancel_run(run_id)

    def submit_manual(self, run_id: str, pid: str, text: str, input_sha256: str, *,
                      user_confirmed: bool = False) -> None:
        return self.execution.submit_manual(run_id, pid, text, input_sha256, user_confirmed=user_confirmed)

    def withdraw_manual(self, run_id: str, pid: str) -> None:
        return self.execution.withdraw_manual(run_id, pid)

    def approve_reduction(self, run_id: str) -> None:
        return self.execution.approve_reduction(run_id)

    def acknowledge_unknown(self, run_id: str, pid: str) -> None:
        return self.execution.acknowledge_unknown(run_id, pid)

    def synthesize(self, run_id: str) -> None:
        return self.synthesis.synthesize(run_id)

    def synthesize_with_model(self, run_id: str, adapter_id: str, spec: ParticipantSpec | None = None) -> None:
        return self.synthesis.synthesize_with_model(run_id, adapter_id, spec)

    def refine(self, supervisor: ParticipantSpec, original: str | None = None, *, refine_id: str | None = None,
               note: str = "", task_id=None, use_memory=True) -> str:
        return self.planning.refine(supervisor, original, refine_id=refine_id, note=note, task_id=task_id, use_memory=use_memory)

    def acknowledge_refine_unknown(self, refine_id: str, turn: int) -> None:
        return self.planning.acknowledge_refine_unknown(refine_id, turn)

    def propose_next(self, run_id: str) -> str:
        return self.planning.propose_next(run_id)

    def acknowledge_proposal_unknown(self, proposal_id: str) -> None:
        return self.planning.acknowledge_proposal_unknown(proposal_id)

    def propose_split(self, goal: str, orchestrator: ParticipantSpec, members: list[ParticipantSpec], sources=None,
                      task_id=None, use_memory=True) -> str:
        return self.planning.propose_split(goal, orchestrator, members, sources, task_id, use_memory)

    def collate(self, run_id: str) -> str:
        return self.reviews.collate(run_id)

    def acknowledge_collation_unknown(self, collation_id: str) -> None:
        return self.reviews.acknowledge_collation_unknown(collation_id)

    def cross_review(self, run_id: str, question: str | None = None) -> list[str]:
        return self.reviews.cross_review(run_id, question)

    def acknowledge_review_unknown(self, review_id: str) -> None:
        return self.reviews.acknowledge_review_unknown(review_id)

    def set_review_disposition(self, review_id: str, finding: int, disposition: str) -> None:
        return self.reviews.set_review_disposition(review_id, finding, disposition)

    def acknowledge_split_unknown(self, split_id: str) -> None:
        return self.planning.acknowledge_split_unknown(split_id)

    def view(self, run_id: str | None = None) -> dict[str, Any]:
        return self.queries.view(run_id)

    def mark_reviewed(self, run_id: str, revision: int, memo: str | None = None) -> None:
        return self.reviews.mark_reviewed(run_id, revision, memo)

    def _model_synthesis_state(self, run_id: str, attempts: dict | None = None) -> dict[str, Any] | None:
        return self.queries._model_synthesis_state(run_id, attempts)

    def acknowledge_synthesis_unknown(self, run_id: str, attempt: str) -> None:
        return self.execution.acknowledge_synthesis_unknown(run_id, attempt)

    def _part(self, run_id: str, pid: str):
        return self.repository._part(run_id, pid)

    def shutdown(self, timeout: float = runner.CLEANUP_LIMIT + 1.0) -> bool:
        return self.execution.shutdown(timeout)

    def wait_idle(self, timeout: float = 30.0) -> bool:
        return self.execution.wait_idle(timeout)

    @property
    def store(self):
        return self.runtime.store

    @store.setter
    def store(self, value):
        self.runtime.store = value

    @property
    def executor(self):
        return self.runtime.executor

    @executor.setter
    def executor(self, value):
        self.runtime.executor = value

    @property
    def max_parallel(self):
        return self.runtime.max_parallel

    @max_parallel.setter
    def max_parallel(self, value):
        self.runtime.max_parallel = value

    @property
    def unsettled_limit(self):
        return self.runtime.unsettled_limit

    @unsettled_limit.setter
    def unsettled_limit(self, value):
        self.runtime.unsettled_limit = value

    @property
    def timeout(self):
        return self.runtime.timeout

    @timeout.setter
    def timeout(self, value):
        self.runtime.timeout = value

    @property
    def work_root(self):
        return self.runtime.work_root

    @work_root.setter
    def work_root(self, value):
        self.runtime.work_root = value

    @property
    def max_real_calls(self):
        return self.runtime.max_real_calls

    @max_real_calls.setter
    def max_real_calls(self, value):
        self.runtime.max_real_calls = value

    @property
    def provider_call_caps(self):
        return self.runtime.provider_call_caps

    @provider_call_caps.setter
    def provider_call_caps(self, value):
        self.runtime.provider_call_caps = value

    @property
    def lock(self):
        return self.runtime.lock

    @lock.setter
    def lock(self, value):
        self.runtime.lock = value

    @property
    def paused(self):
        return self.runtime.paused

    @paused.setter
    def paused(self, value):
        self.runtime.paused = value

    @property
    def _closing(self):
        return self.runtime.closing

    @_closing.setter
    def _closing(self, value):
        self.runtime.closing = value

    @property
    def _workers(self):
        return self.runtime.workers

    @_workers.setter
    def _workers(self, value):
        self.runtime.workers = value

    @property
    def _synthesis(self):
        return self.runtime.syntheses

    @_synthesis.setter
    def _synthesis(self, value):
        self.runtime.syntheses = value

    @property
    def _supervising(self):
        return self.runtime.upper_workers

    @_supervising.setter
    def _supervising(self, value):
        self.runtime.upper_workers = value
