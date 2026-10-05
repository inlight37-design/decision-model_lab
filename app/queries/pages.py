"""Bounded UI pages over the existing public projection, never an admission cache."""
import base64
from bisect import bisect_left
import copy
import json
import math

from app.domain import ControllerError
from core import runner


def limit_value(value=25):
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        value = int(value)
    if type(value) is not int or not 1 <= value <= 100:
        raise ControllerError('한 번에 1~100개까지 조회할 수 있습니다.')
    return value


def decode(cursor, scope):
    if cursor is None:
        return None
    try:
        if not isinstance(cursor, str) or len(cursor) > 2048:
            raise ValueError()
        value = json.loads(base64.b64decode(cursor, altchars=b'-_', validate=True))
        owner, stamp, key = value
        if (owner != scope or type(stamp) not in (int, float) or not math.isfinite(stamp)
                or not isinstance(key, str) or not key or len(key) > 256):
            raise ValueError()
        return stamp, key
    except (ValueError, TypeError, UnicodeError):
        raise ControllerError('목록 위치가 올바르지 않습니다. 처음부터 다시 조회하세요.') from None


def encode(scope, key):
    return base64.urlsafe_b64encode(json.dumps([scope, *key], ensure_ascii=False).encode()).decode()


def indexed(rows, key):
    ascending = sorted(rows, key=key)
    return ascending, [key(row) for row in ascending]


def page(index, scope, after, limit):
    rows, keys = index
    end = bisect_left(keys, after) if after is not None else len(rows)
    start = max(0, end - limit)
    items = list(reversed(rows[start:end]))
    return items, {'total': len(rows), 'count': len(items), 'limit': limit,
                   'next': encode(scope, keys[start]) if start else None}


def compact(task, runs=()):
    result = {**task, 'run_count': len(task['runs']), 'runs': list(runs)}
    result['readiness'] = {**task['readiness'], 'dependencies': [
        {k: v for k, v in dep.items() if k != 'evidence'} for dep in task['readiness']['dependencies']]}
    return result


class BrowserPages:
    """Rebuild after writes/runtime changes; cold or changing ledgers remain linear.

    The cache is disposable, process-local, public data. Commands always use the
    fresh PublicQueries path. Never retain a projection built in a transaction.
    """
    def __init__(self, queries):
        self.queries = queries
        self.key = self.snapshot = None

    def _snapshot(self):
        q = self.queries; rt = q.runtime
        token = q.store.read_token()
        key = (token, rt.paused, rt.max_parallel, rt.unsettled_limit, rt.max_real_calls,
               tuple(sorted(rt.provider_call_caps.items())), rt.executor.name, runner.lingering(),
               tuple(sorted((rid, worker[2]) for rid, worker in rt.syntheses.items())))
        if token is None or key != self.key:
            snapshot = q.overview()
            tasks = {task['task_id']: task for task in snapshot['tasks']}
            task_index = indexed(tasks.values(), lambda t: (t['created_at'], t['task_id']))
            timelines = {key: indexed(task['runs'], lambda r: (r['created_at'], r['run_id'])) for key, task in tasks.items()}
            priority = {'refine_unknown': 4, 'split_unknown': 4, 'problem': 3, 'my_turn': 2, 'dependency': 1, 'prepare': 0}
            inbox_index = indexed(snapshot['inbox'], lambda row: (priority[row['kind']], row['id']))
            built = snapshot, tasks, task_index, timelines, inbox_index
            if token is None:
                return built
            self.key, self.snapshot = key, built
        return self.snapshot

    def browse(self, *, task=None, run=None, tasks_after=None, runs_after=None, inbox_after=None, limit=25):
        limit = limit_value(limit)
        task_anchor = decode(tasks_after, 'tasks')
        inbox_anchor = decode(inbox_after, 'inbox')
        q = self.queries
        with q.runtime.lock:
            if run is not None:
                owner = q.repository._run(run)['task_id']
                if task is not None and owner != task:
                    raise ControllerError('선택한 실행과 작업이 다릅니다.')
                task = owner
            run_scope = 'runs:' + (task or '')
            run_anchor = decode(runs_after, run_scope)
            if runs_after is not None and task is None:
                raise ControllerError('실행 목록의 작업을 먼저 선택하세요.')
            snapshot, tasks, task_index, timelines, inbox_index = self._snapshot()
            if task is not None and task not in tasks:
                raise ControllerError('작업을 찾을 수 없습니다.')
            cards, task_page = page(task_index, 'tasks', task_anchor, limit)
            inbox, inbox_page = page(inbox_index, 'inbox', inbox_anchor, limit)
            result = {**snapshot, 'tasks': [compact(t) for t in cards], 'inbox': inbox,
                      'focus_task': None, 'focus_run': None, 'pages': {'tasks': task_page, 'inbox': inbox_page}}
            # Cards need no full plan text; the selected task has the complete plan.
            for card in result['tasks']:
                card.pop('plan', None)
                card.pop('readiness', None)
            if task is not None:
                timeline, run_page = page(timelines[task], run_scope, run_anchor, limit)
                result['focus_task'] = compact(tasks[task], timeline)
                result['pages']['runs'] = run_page
                if run is not None:
                    result['focus_run'] = next(r for r in tasks[task]['runs'] if r['run_id'] == run)
            result['runs'] = q.view(run, _global=False)['runs'] if run is not None else []
            return copy.deepcopy(result)

    def choices(self, *, query='', after=None, limit=25):
        limit = limit_value(limit)
        if not isinstance(query, str) or len(query) > 120:
            raise ControllerError('작업 검색어는 120자까지입니다.')
        scope = 'choices:' + query
        anchor = decode(after, scope)
        clauses, args = [], []
        if query:
            clauses.append('instr(lower(title), lower(?)) > 0'); args.append(query)
        if anchor:
            clauses.append('(created_at, task_id) < (?, ?)'); args.extend(anchor)
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        with self.queries.runtime.lock:
            rows = [dict(r) for r in self.queries.store.rows('SELECT task_id, title, created_at FROM tasks' + where +
                    ' ORDER BY created_at DESC, task_id DESC LIMIT ?', *args, limit + 1)]
        visible = rows[:limit]
        return {'items': visible, 'next': encode(scope, (visible[-1]['created_at'], visible[-1]['task_id']))
                if len(rows) > limit else None}
