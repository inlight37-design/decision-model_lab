"""Read-only work readiness and action projections. No execution or persisted inbox."""
import json


def plans(store):
    return {r['task_id']: {**dict(r), 'depends_on': json.loads(r['depends_on'])}
            for r in store.rows('SELECT * FROM task_plans')}


def planning_states(store):
    """Task-linked calls that have not yet become part of a run timeline."""
    rows = store.rows("SELECT task_id, state FROM splits WHERE used_by IS NULL AND state IN ('running', 'unknown') "
                      "UNION SELECT json_extract(e.payload, '$.memory.task_id') AS task_id, t.state "
                      "FROM refine_turns t JOIN refinements f USING (refine_id) "
                      "JOIN events e ON e.run_id = f.refine_id AND e.kind = 'memory_selected' "
                      "WHERE f.run_id IS NULL AND t.state IN ('running', 'unknown')")
    result = {}
    for row in rows:
        if row['task_id']:
            result.setdefault(row['task_id'], set()).add(row['state'])
    return result


def steps(run, held=None):
    gate = run['gate']
    public = gate['revealed'] or gate.get('collected', False)
    states = {p['state'] for p in run['participants']}
    reviews = [*(run.get('cross_review') or {}).get('reviews', []), *run.get('answer_revisions', [])]
    reviews += [c for v in run.get('answer_revisions', []) for c in v['rechecks']]
    reviews += [*run.get('proposals', []), *run.get('collations', [])]
    checked = {r['state'] for r in reviews}
    synthesis = (run.get('model_synthesis') or {}).get('status')
    if synthesis:
        checked.add(synthesis)
    collection = 'done' if public else 'blocked' if ('unknown' in states or run['cancel_requested']
        or gate['status'] == 'quorum_blocked' or ('queued' in states and held)) else 'waiting'
    review = ('blocked' if 'unknown' in checked or ('queued' in checked and held) else
              'waiting' if checked & {'running', 'queued'} else 'done') if reviews or synthesis else 'optional'
    return [dict(id='input', kind='prepare', label='입력 고정', state='done', depends_on=[]),
            dict(id='collect', kind='execution', label='답 수집·공개', state=collection, depends_on=['input']),
            dict(id='review', kind='review', label='검토·수정·정리', state=review, depends_on=['collect']),
            dict(id='decision', kind='human', label='사람의 판단',
                 state=('done' if run['reviewed'] else 'ready') if public and review in ('done', 'optional') else 'waiting',
                 depends_on=['collect', *(['review'] if reviews or synthesis else [])])]


def project_tasks(tasks, specifications, planning=None):
    """Prerequisites are completed public human judgments under the current plan.

    Changes affect readiness for new runs only; they do not cancel admitted work.
    Missing/cyclic persisted references fail closed, even if external corruption
    bypassed the command validation.
    """
    by_id = {t['task_id']: t for t in tasks}
    planning = planning or {}
    complete = {}
    fresh = {}
    for task in tasks:
        key = task['task_id']; plan = specifications.get(key)
        latest = task['runs'][-1] if task['runs'] else None
        frozen = ((latest or {}).get('role_config') or {}).get('task_plan')
        fresh[key] = not plan or bool(frozen and frozen['revision'] == plan['revision'])
        if plan:
            current = [r for r in task['runs'] if (r['role_config'].get('task_plan') or {}).get('revision') == plan['revision']]
            unsafe = any(r.get('unsettled') or r.get('active') for r in task['runs'])
            complete[key] = bool(current) and all(r['status'] == 'done' for r in current) and not unsafe
            task['status'] = next((s for s in ('problem', 'my_turn', 'working') if any(r['status'] == s for r in current)),
                                  'done' if current else 'my_turn')
            if any(r.get('unsettled') for r in task['runs']):
                task['status'] = 'problem'
        else:
            complete[key] = task['status'] == 'done'
        if planning.get(key):
            complete[key] = False
            task['status'] = 'problem' if 'unknown' in planning[key] or task['status'] == 'problem' else 'working'
    # Monotone fixed point. Cycles are invalid, so do not call a cycle completed.
    pending = set(by_id); finished = {}
    while pending:
        ready = [key for key in pending if all(d not in pending for d in specifications.get(key, {}).get('depends_on', []))]
        if not ready:
            break
        for key in ready:
            finished[key] = complete[key] and all(finished.get(d, False) for d in specifications.get(key, {}).get('depends_on', []))
            pending.remove(key)
    for task in tasks:
        key = task['task_id']; plan = specifications.get(key)
        dependencies = []
        for dependency in (plan or {}).get('depends_on', []):
            other = by_id.get(dependency)
            dependencies.append({'task_id': dependency, 'title': other['title'] if other else '찾을 수 없는 작업',
                                 'complete': finished.get(dependency, False),
                                 'reason': None if finished.get(dependency, False) else
                                 'missing' if other is None else 'plan_changed' if not fresh[dependency] else
                                 'dependency_cycle' if dependency in pending else 'not_completed',
                                 'plan_revision': specifications.get(dependency, {}).get('revision', 0),
                                 'evidence': [{'run_id': r['run_id'], 'result_revision': r.get('result_revision')}
                                              for r in other['runs'] if r['status'] == 'done' and (dependency not in specifications or
                                              (r['role_config'].get('task_plan') or {}).get('revision') == specifications[dependency]['revision'])]
                                             if other and finished.get(dependency) else []})
        task['plan'] = plan
        task['readiness'] = {'dependencies_met': all(d['complete'] for d in dependencies),
                             'dependencies': dependencies, 'plan_fresh': fresh[key],
                             'complete': finished.get(key, False)}
        if task['status'] == 'done' and not fresh[key]:
            task['status'] = 'my_turn'
        if dependencies and not task['readiness']['dependencies_met'] and task['status'] not in ('working', 'problem'):
            task['status'] = 'blocked'
    return tasks


def inbox(tasks):
    result = []
    for task in tasks:
        ready = task['readiness']
        for dep in ready['dependencies']:
            if not dep['complete']:
                result.append(dict(id=f"{task['task_id']}:dependency:{dep['task_id']}", kind='dependency',
                                   task_id=task['task_id'], run_id=None, target_task=dep['task_id'],
                                   title=task['title'], action='선행 작업 확인',
                                   reason=dep['title'] + ' · ' + {'missing': '작업 없음', 'plan_changed': '계획 변경 뒤 결과 확인 필요',
                                   'dependency_cycle': '순환 의존성', 'not_completed': '아직 판단 완료되지 않음'}[dep['reason']]))
        if (not task['runs'] or not ready['plan_fresh']) and ready['dependencies_met'] and task['status'] not in ('working', 'problem'):
            result.append(dict(id=f"{task['task_id']}:prepare", kind='prepare', task_id=task['task_id'], run_id=None,
                               title=task['title'], action='실행 준비', reason='저장한 계획의 새 실행을 준비하세요.'))
        for run in task['runs']:
            if (task['plan'] and (run['role_config'].get('task_plan') or {}).get('revision') != task['plan']['revision']
                    and not run.get('unsettled') and not run.get('active')):
                continue  # historical plans stay in the timeline, not the current action inbox
            if run['status'] in ('my_turn', 'problem'):
                result.append(dict(id=f"{run['run_id']}:attention", kind=run['status'], task_id=task['task_id'],
                                   run_id=run['run_id'], title=task['title'], action=run['action'] or '실행 확인',
                                   reason=run['question']))
    return result


def admission(snapshot):
    """Explain controller capacity independently of task dependencies or model choice."""
    reasons = []
    if snapshot['paused']:
        reasons.append({'code': 'paused', 'message': '재시작 뒤 멈춰 있습니다. 기존 실행을 확인하고 이어서 시작하세요.'})
    if snapshot['unsettled']['count']:
        reasons.append({'code': 'unsettled', 'message': '끝났는지 모르는 호출이 있습니다. 종료 확인이 먼저 필요합니다.'})
    if snapshot['slots']['used'] >= snapshot['slots']['cap']:
        reasons.append({'code': 'capacity', 'message': '호출 자리가 모두 사용 중입니다.'})
    budget = snapshot['live_call_budget']
    if budget['cap'] is not None and budget['used'] >= budget['cap']:
        reasons.append({'code': 'budget', 'message': '이 원장의 실제 CLI 호출 상한을 다 썼습니다. 기존 기록은 보존합니다.'})
    return {'reasons': reasons, 'final_check': '선행 조건과 선택한 역할·모델의 실행 조건은 시작할 때 다시 확인합니다.'}


def unattached_inputs(refinements, splits):
    result = []
    for refinement in refinements:
        for turn in refinement['turns']:
            if turn['state'] == 'unknown':
                result.append(dict(id=f"{refinement['refine_id']}:{turn['turn']}:unknown", kind='refine_unknown',
                                   refine_id=refinement['refine_id'], turn=turn['turn'], title='질문 다듬기',
                                   action='종료를 직접 확인', reason='실행에 연결하지 않은 다듬기 차례가 끝났는지 모릅니다.'))
    for split in splits:
        if split['state'] == 'unknown':
            result.append(dict(id=split['split_id'] + ':unknown', kind='split_unknown', split_id=split['split_id'],
                               title='분담 제안', action='종료를 직접 확인', reason='실행에 연결하지 않은 분담 제안이 끝났는지 모릅니다.'))
    return result
