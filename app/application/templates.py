"""Immutable reusable work drafts. Never copy execution authority or launch a call."""
from __future__ import annotations

import hashlib
import json
import time
import uuid

from app.context.inputs import _checked_sources
from app.domain import ControllerError, storable
from app.roles import freeze
from app import source_document


FIELDS = {'question', 'task_title', 'role_board', 'models', 'min_independent',
          'quorum_policy', 'sources', 'assignments', 'use_memory'}
SLOTS = ('supervisor', 'orchestrator', 'general', 'isolated')


class TemplateService:
    def __init__(self, runtime, inputs):
        self.runtime, self.store, self.inputs = runtime, runtime.store, inputs

    def validate(self, draft, roster, bindings=None):
        if not isinstance(draft, dict) or set(draft) - FIELDS:
            raise ControllerError('템플릿에는 작업 설정만 저장합니다. 실행·승인 정보는 넣을 수 없습니다.')
        question = draft.get('question')
        if not isinstance(question, str) or not question.strip() or len(question) > 16000:
            raise ControllerError('템플릿 질문은 1~16000자여야 합니다.')
        board = draft.get('role_board')
        if not isinstance(board, dict):
            raise ControllerError('템플릿에 역할판이 필요합니다.')
        members = board.get('general') or board.get('isolated')
        if not isinstance(members, list) or any(not isinstance(pid, str) or pid not in roster for pid in members):
            raise ControllerError('현재 명단에 없는 팀원이 있습니다.')
        participants = [roster[pid] for pid in members]
        try:
            freeze(board, participants, roster)
        except ValueError as exc:
            raise ControllerError(str(exc)) from None
        assigned = {pid for slot in SLOTS for pid in board[slot]}
        models = draft.get('models', {})
        if not isinstance(models, dict) or set(models) - assigned:
            raise ControllerError('배치한 카드의 모델만 저장합니다.')
        actual = {pid: {key: getattr(roster[pid], key) for key in
                       ('provider', 'transport', 'adapter_id', 'model')} for pid in sorted(assigned)}
        if any(not isinstance(model, str) or actual[pid]['model'] != model for pid, model in models.items()):
            raise ControllerError('저장할 모델이 현재 선택과 다릅니다.')
        if bindings is not None and actual != bindings:
            raise ControllerError('템플릿의 카드·모델 구성이 현재 명단과 다릅니다. 새 설정으로 준비하세요.')
        sources = draft.get('sources', [])
        if not isinstance(sources, list) or any(not isinstance(s, dict) or set(s) != {'name', 'text'} for s in sources):
            raise ControllerError('자료는 이름과 텍스트 사본이어야 합니다.')
        checked = _checked_sources([(s['name'], s['text']) for s in sources])
        minimum = draft.get('min_independent', 1)
        if type(minimum) is not int:
            raise ControllerError('정족수는 정수여야 합니다.')
        # A template remembers the mode, never an approved refinement turn. Validate
        # the remaining input contract without manufacturing such an approval.
        self.inputs.prepare_run(question, participants, min_independent=minimum,
            quorum_policy=draft.get('quorum_policy', 'independent_only'),
            role_board={**board, 'input_mode': 'original'}, roster=roster,
            sources=[(name, data.decode('utf-8')) for name, data in checked],
            assignments=draft.get('assignments'), task_title=draft.get('task_title') or None,
            use_memory=draft.get('use_memory', True))
        return actual

    def save(self, name, draft, roster):
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80 or not storable(name):
            raise ControllerError('템플릿 이름은 1~80자의 올바른 글이어야 합니다.')
        bindings = self.validate(draft, roster)
        payload = json.dumps({'version': 1, 'draft': draft, 'bindings': bindings},
                             ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        key = 'tpl-' + uuid.uuid4().hex
        with self.runtime.lock, self.store.tx() as tx:
            if self.runtime.closing:
                raise ControllerError('controller is shutting down')
            if self.store.row('SELECT COUNT(*) AS n FROM work_templates')['n'] >= 100:
                raise ControllerError('템플릿은 100개까지 보관합니다. 쓰지 않는 템플릿을 정리하세요.')
            tx.execute('INSERT INTO work_templates VALUES (?, ?, ?, ?, ?)', key, name.strip(), time.time(), payload, digest)
            tx.event(key, 'template_saved', sha256=digest)
        return {'template_id': key, 'sha256': digest}

    def list(self):
        return [dict(row) for row in self.store.rows(
            'SELECT template_id, name, created_at, sha256 FROM work_templates ORDER BY created_at DESC, template_id')]

    def load(self, key):
        row = self.store.row('SELECT * FROM work_templates WHERE template_id = ?', key)
        if row is None:
            raise ControllerError('템플릿을 찾을 수 없습니다.')
        try:
            if hashlib.sha256(row['payload'].encode('utf-8')).hexdigest() != row['sha256']:
                raise ValueError('hash')
            data = json.loads(row['payload'])
            if data['version'] != 1:
                raise ValueError('version')
            sources = _checked_sources([(s['name'], s['text']) for s in data['draft'].get('sources', [])])
        except (ValueError, TypeError, KeyError) as exc:
            raise ControllerError('저장된 템플릿이 손상되었거나 지원하지 않는 형식입니다.') from exc
        return {'template_id': row['template_id'], 'name': row['name'], 'sha256': row['sha256'], **data,
                'sources': [source_document.listing(name, raw) for name, raw in sources]}

    def delete(self, key, digest):
        with self.runtime.lock, self.store.tx() as tx:
            if not tx.execute('DELETE FROM work_templates WHERE template_id = ? AND sha256 = ?', key, digest):
                raise ControllerError('목록이 바뀌었습니다. 템플릿을 다시 확인하세요.')
            tx.event(key, 'template_deleted', sha256=digest)

    def export(self, key):
        item = self.load(key)
        return {'format': 'decision-work-template/1', **{k: item[k] for k in ('name', 'draft', 'bindings', 'sha256')}}

    def import_copy(self, document, roster):
        if (not isinstance(document, dict) or set(document) != {'format', 'name', 'draft', 'bindings', 'sha256'}
                or document['format'] != 'decision-work-template/1'):
            raise ControllerError('지원하는 템플릿 파일이 아닙니다.')
        payload = json.dumps({'version': 1, 'draft': document['draft'], 'bindings': document['bindings']},
                             ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        if not storable(payload) or hashlib.sha256(payload.encode('utf-8')).hexdigest() != document['sha256']:
            raise ControllerError('템플릿 파일의 해시가 맞지 않습니다.')
        self.validate(document['draft'], roster, document['bindings'])
        return self.save(document['name'], document['draft'], roster)
