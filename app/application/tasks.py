"""Optional work plans and local prerequisites; no scheduler or model authority."""
import json
import time
import uuid

from app.domain import ControllerError, storable
from app import workflow


class TaskService:
    def __init__(self, runtime, queries):
        self.runtime, self.store, self.queries = runtime, runtime.store, queries

    def save(self, payload, *, task_id=None):
        fields = {'title', 'goal', 'done_when', 'depends_on', 'revision'}
        if not isinstance(payload, dict) or set(payload) != fields:
            raise ControllerError('작업 계획에는 제목·목표·완료 기준·선행 작업·보고 있는 판이 필요합니다.')
        for key, limit in (('title', 120), ('goal', 16000), ('done_when', 4000)):
            value = payload[key]
            if not isinstance(value, str) or not value.strip() or len(value) > limit or not storable(value):
                raise ControllerError(f'{key}: 1~{limit}자의 올바른 글을 적으세요.')
        dependencies = payload['depends_on']
        if (not isinstance(dependencies, list) or len(dependencies) > 16 or
                any(not isinstance(d, str) or not d for d in dependencies) or len(set(dependencies)) != len(dependencies)):
            raise ControllerError('선행 작업은 중복 없이 최대 16개까지 고릅니다.')
        if type(payload['revision']) is not int or payload['revision'] < 0:
            raise ControllerError('보고 있는 계획 판이 올바르지 않습니다.')
        with self.runtime.lock, self.store.tx() as tx:
            if self.runtime.closing:
                raise ControllerError('controller is shutting down')
            creating = task_id is None
            task_id = task_id or 't-plan-' + uuid.uuid4().hex
            task = self.store.row('SELECT * FROM tasks WHERE task_id = ?', task_id)
            current = self.store.row('SELECT * FROM task_plans WHERE task_id = ?', task_id)
            revision = current['revision'] if current else 0
            if (not creating and task is None) or payload['revision'] != revision:
                raise ControllerError('작업이 없거나 계획이 바뀌었습니다. 다시 열어 확인하세요.')
            if task_id in dependencies:
                raise ControllerError('자기 작업을 선행 작업으로 둘 수 없습니다.')
            for dep in dependencies:
                if not self.store.row('SELECT 1 FROM tasks WHERE task_id = ?', dep):
                    raise ControllerError('찾을 수 없는 선행 작업입니다.')
            graph = {key: p['depends_on'] for key, p in workflow.plans(self.store).items()}
            graph[task_id] = dependencies
            pending, visited = list(dependencies), set()
            while pending:
                key = pending.pop()
                if key == task_id:
                    raise ControllerError('선행 작업이 순환합니다. 서로 기다리는 연결을 풀어주세요.')
                if key not in visited:
                    visited.add(key); pending.extend(graph.get(key, []))
            if task and self._active(task_id):
                raise ControllerError('진행 중이거나 종료 미확인인 작업의 계획은 바꿀 수 없습니다.')
            plan = {key: payload[key].strip() for key in ('title', 'goal', 'done_when')}
            plan.update(task_id=task_id, revision=revision + 1, depends_on=dependencies)
            if creating:
                tx.execute('INSERT INTO tasks VALUES (?, ?, ?)', task_id, plan['title'], time.time())
            else:
                tx.execute('UPDATE tasks SET title = ? WHERE task_id = ?', plan['title'], task_id)
            if current:
                changed = tx.execute('UPDATE task_plans SET revision = ?, title = ?, goal = ?, done_when = ?, depends_on = ? '
                                     'WHERE task_id = ? AND revision = ?', plan['revision'], plan['title'], plan['goal'],
                                     plan['done_when'], json.dumps(dependencies), task_id, revision)
                if not changed:
                    raise ControllerError('계획이 바뀌었습니다. 다시 열어 확인하세요.')
            else:
                tx.execute('INSERT INTO task_plans VALUES (?, ?, ?, ?, ?, ?)', task_id, plan['revision'], plan['title'],
                           plan['goal'], plan['done_when'], json.dumps(dependencies))
            tx.event(task_id, 'task_plan_saved', plan=plan)
            return plan

    def _active(self, task_id):
        if workflow.planning_states(self.store).get(task_id):
            return True
        if self.store.row("SELECT 1 FROM participants p JOIN runs r USING (run_id) WHERE r.task_id = ? "
                          "AND (p.state IN ('running', 'unknown') OR (NOT r.cancel_requested "
                          "AND p.state IN ('queued', 'awaiting_user')))", task_id):
            return True
        snapshot = self.queries.view(_summary=True)
        task = next((t for t in snapshot['tasks'] if t['task_id'] == task_id), None)
        return bool(task and any(r['active'] or r['unsettled'] for r in task['runs']))

    def require_ready(self, task_id):
        if task_id is None or not self.store.row('SELECT 1 FROM task_plans WHERE task_id = ?', task_id):
            return None
        with self.runtime.lock:
            snapshot = self.queries.view(_summary=True)
            task = next(t for t in snapshot['tasks'] if t['task_id'] == task_id)
            blocked = [d for d in task['readiness']['dependencies'] if not d['complete']]
            if blocked:
                raise ControllerError('선행 작업이 끝나지 않았습니다: ' + ', '.join(d['title'] for d in blocked))
            return {**task['plan'], 'dependency_evidence': task['readiness']['dependencies']}
