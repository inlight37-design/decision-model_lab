"""Search only already-public projections. No database or executor capability."""
import json

from app.domain import ControllerError, storable


def search(snapshot, query, *, task_id=None, kind=None, limit=30):
    if not isinstance(query, str) or not storable(query) or not 1 <= len(query.strip()) <= 200:
        raise ControllerError("검색어는 1~200자의 글로 적습니다.")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ControllerError("검색 결과 한도는 1~100입니다.")
    if task_id is not None and not isinstance(task_id, str):
        raise ControllerError("task_id must be a string")
    kinds = ('question', 'answer', 'review', 'decision', 'synthesis', 'source')
    if kind is not None and kind not in kinds:
        raise ControllerError("지원하지 않는 검색 종류입니다.")
    needle = query.strip().casefold()
    result, total = [], 0
    titles = {t['task_id']: t['title'] for t in snapshot['tasks']}

    def add(run, type_, ref, title, text):
        nonlocal total
        if kind is not None and kind != type_:
            return
        text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
        # Direct text matching supports exact IDs, Korean phrases and hashes too.
        searchable = title + '\n' + text
        if needle not in searchable.casefold():
            return
        total += 1
        if len(result) >= limit:
            return
        at = searchable.casefold().find(needle)
        start = max(0, at - 70)
        snippet = ('…' if start else '') + searchable[start:start + 300]
        if start + 300 < len(searchable):
            snippet += '…'
        result.append({'run_id': run['run_id'], 'task_id': run['task_id'], 'kind': type_,
                       'ref': ref, 'title': title, 'snippet': snippet,
                       'task_title': titles.get(run['task_id'], ''), 'phase': run['phase']})

    for run in snapshot['runs']:
        if task_id is not None and run['task_id'] != task_id:
            continue
        add(run, 'question', run['run_id'], run['question'],
            run['run_id'] + '\n' + titles.get(run['task_id'], ''))
        for source in run['sources']:
            add(run, 'source', source['name'], source['name'],
                source['sha256'] + '\n' + json.dumps(source.get('provenance', {}), ensure_ascii=False))
        for participant in run['participants']:
            if participant.get('draft') is not None:
                add(run, 'answer', participant['pid'], participant['label'], participant['draft'])
        review = run.get('cross_review')
        for variant in run.get('answer_revisions', []):
            if variant.get('reply'):
                add(run, 'answer', variant['revision_id'], '수정 답 · ' + variant['author']['label'], variant['reply']['answer'])
                add(run, 'review', variant['revision_id'], '수정 대응 · ' + run['question'], variant['reply']['responses'])
            for check in variant['rechecks']:
                if check.get('reply'):
                    add(run, 'review', check['check_id'], '재검토 · ' + run['question'], check['reply'])
        if review:
            add(run, 'review', run['run_id'], '교차검토 · ' + run['question'], review)
        if run.get('reviewed'):
            add(run, 'decision', run['run_id'], '사람의 판단 · ' + run['question'], run.get('review_memo') or '')
        for collation in run.get('collations', []):
            if collation.get('reply'):
                add(run, 'synthesis', collation['collation_id'], '결과 모음 · ' + run['question'], collation['reply'])
        for synthesis in run.get('model_syntheses', []):
            if synthesis.get('result'):
                add(run, 'synthesis', synthesis['attempt'], '합성 · ' + run['question'], synthesis['result'])
        if run.get('synthesis') and not run.get('model_syntheses'):
            add(run, 'synthesis', run['run_id'], '대조 · ' + run['question'], run['synthesis'])
    return {'query': query.strip(), 'items': result, 'total': total, 'truncated': total > len(result),
            'scope': 'public_projection', 'model_calls': 0}
