"""Explicit revision/recheck commands over immutable answer variants: post-reveal isolated or collected general (GR-2)."""
from __future__ import annotations
from dataclasses import asdict
import json
import os
import re
import time
import uuid

from app import revisions as format_
from app.domain import ControllerError, ParticipantSpec
from app.execution.seats import REVISION_SEAT, RECHECK_SEAT
from app.state import ACCEPTED, CLI, RUNNING, UNKNOWN


class RevisionService:
    def __init__(self, runtime, execution, inputs, invocations, repository):
        self.runtime, self.store = runtime, runtime.store
        self.execution, self.inputs, self.invocations, self.repository = execution, inputs, invocations, repository

    @staticmethod
    def _answer(row):
        reply = json.loads(row['result'] or '{}').get('reply')
        if row['state'] != ACCEPTED or not reply or format_.digest(reply['answer']) != reply['sha256']:
            raise ControllerError('수정 답의 수용 상태와 원문 해시를 확인할 수 없습니다.')
        return reply

    def _context(self, run_id, pid):
        run = self.repository._run(run_id)
        gate = self.repository._gate(run_id)
        if gate.general and (not gate.collected or run['cancel_requested']):
            raise ControllerError('일반 팀원의 수정은 모두 끝난(모음으로 닫힌) 실행의 교차검토 뒤에 준비합니다.')
        if not gate.general and not gate.revealed:
            raise ControllerError('수정은 격리 초안의 공개와 교차검토 뒤에 준비합니다.')
        part = self.repository._part(run_id, pid)
        spec = ParticipantSpec(**json.loads(part['spec']))
        if part['state'] != ACCEPTED or spec.transport != CLI:
            raise ControllerError('받은 답을 낸 CLI 팀원만 수정 작성자로 부릅니다.')
        self.invocations._cli_card(spec, '수정 작성자')
        original = self.store.row('SELECT text, sha256 FROM drafts WHERE run_id = ? AND pid = ?', run_id, pid)
        if original is None or format_.digest(original['text']) != original['sha256']:
            raise ControllerError('원래 답의 해시를 확인할 수 없습니다.')
        reviews = self.store.rows('SELECT * FROM reviews WHERE run_id = ? ORDER BY seq', run_id)
        if not reviews or any(r['state'] in ('queued', RUNNING, UNKNOWN) for r in reviews):
            raise ControllerError('교차검토가 끝나고 종료를 확인한 뒤 수정합니다.')
        existing = self.store.rows('SELECT * FROM answer_revisions WHERE run_id = ? AND pid = ? ORDER BY created_at, revision_id', run_id, pid)
        if len(existing) >= format_.MAX_REVISIONS:
            raise ControllerError(f'팀원 하나의 수정은 실행마다 {format_.MAX_REVISIONS}번까지입니다. 실패도 포함합니다.')
        if any(r['state'] in (RUNNING, UNKNOWN) for r in existing):
            raise ControllerError('앞선 수정 호출의 종료를 먼저 확인하세요.')
        findings = []
        for review in reviews:
            if review['state'] != ACCEPTED:
                continue
            targets = json.loads(review['targets'])
            dispositions = {r['finding']: r['disposition'] for r in self.store.rows(
                'SELECT finding, disposition FROM review_dispositions WHERE review_id = ?', review['review_id'])}
            for index, finding in enumerate(json.loads(review['result'])['reply']['findings']):
                target = targets[finding['target']]
                if target['pid'] != pid:
                    continue
                if target['sha256'] != original['sha256'] or format_.digest(target['text']) != original['sha256']:
                    raise ControllerError('교차검토가 다른 판의 답을 가리킵니다.')
                findings.append({'id': review['review_id'] + ':' + str(index),
                    'source_sha256': target['sha256'], 'disposition': dispositions.get(index, 'unresolved'), **finding})
        parent = next((r for r in reversed(existing) if r['state'] == ACCEPTED), None)
        base = {'revision_id': None, 'text': original['text'], 'sha256': original['sha256']}
        checks = []
        if parent is not None:
            reply = self._answer(parent)
            base = {'revision_id': parent['revision_id'], 'text': reply['answer'], 'sha256': reply['sha256']}
            rows = self.store.rows('SELECT * FROM revision_checks WHERE revision_id = ? ORDER BY created_at, check_id', parent['revision_id'])
            if any(r['state'] in (RUNNING, UNKNOWN) for r in rows) or not any(r['state'] == ACCEPTED for r in rows):
                raise ControllerError('앞선 수정 답을 다른 팀원이 재검토한 뒤 다음 판을 준비합니다.')
            for row in rows:
                if row['state'] != ACCEPTED:
                    continue
                if row['answer_sha256'] != base['sha256'] or format_.digest(row['answer']) != base['sha256']:
                    raise ControllerError('재검토가 다른 판을 가리킵니다.')
                checked = json.loads(row['result'])['reply']
                checks.append({'check_id': row['check_id'], 'reply': checked})
                for index, finding in enumerate(checked['findings']):
                    findings.append({'id': row['check_id'] + ':' + str(index), 'source_sha256': base['sha256'],
                                     'disposition': 'unresolved', **finding})
        if not findings:
            raise ControllerError('이 답에 연결된 검토 지적이 없습니다.')
        if not gate.general:
            snapshot = {'run_id': run_id, 'pid': pid, 'question': run['question'],
                        'original': dict(original), 'base': base, 'findings': findings, 'prior_checks': checks,
                        'sources': self.repository.sources(run_id), 'source_folder': self.inputs._source_root(run_id)}
            return spec, snapshot
        # 일반 팀원(GR-2): 전체 목표와 자기 맡은 일, 자기 자료 목록만 고정한다. 맡긴 일의 입력 전문(assignment prompt)은
        # 다시 쓰지 않는다 — 자동 기억 전달문이 들어 있을 수 있다. 다른 팀원의 자료·공통 자료 폴더는 넣지 않는다.
        work = self.inputs._checked_assignment(run_id, pid)
        listed = [{key: source[key] for key in ('name', 'sha256', 'bytes')} for source in json.loads(work['sources'])]
        snapshot = {'contract': format_.GENERAL_CONTRACT, 'mode': 'general', 'run_id': run_id, 'pid': pid,
                    'goal': run['question'], 'task': work['task'], 'assignment_sha256': work['input_sha256'],
                    'original': dict(original), 'base': base, 'findings': findings, 'prior_checks': checks,
                    'sources': listed, 'source_folder': self.inputs._member_source_root(run_id, pid) if listed else None,
                    'source_bodies': 'own_assigned_only', 'memory_pack': 'not_added'}
        return spec, snapshot

    def prepare(self, run_id, pid, revision_id=None):
        with self.runtime.lock:
            spec, snapshot = self._context(run_id, pid)
            revision_id = revision_id or 'rev-' + uuid.uuid4().hex
            if not isinstance(revision_id, str) or not re.fullmatch('rev-[0-9a-f]{32}', revision_id):
                raise ControllerError('잘못된 수정 판 ID입니다.')
            text = format_.prompt(snapshot, revision_id[4:])
            manifest = {'revision_id': revision_id, 'run_id': run_id, 'pid': pid,
                        'parent_id': snapshot['base']['revision_id'], 'author': asdict(spec),
                        'snapshot': snapshot, 'snapshot_sha256': format_.digest(format_.encoded(snapshot)),
                        'prompt': text, 'input_sha256': format_.digest(text), 'calls': 1}
            return {**manifest, 'confirmation': format_.digest(format_.encoded(manifest))}

    def revise(self, run_id, pid, revision_id, confirmation):
        with self.runtime.lock:
            if not revision_id:
                raise ControllerError('먼저 수정 입력을 미리 확인하세요.')
            if self.runtime.closing:
                raise ControllerError('controller is shutting down')
            prepared = self.prepare(run_id, pid, revision_id)
            if not isinstance(confirmation, str) or confirmation != prepared['confirmation']:
                raise ControllerError('답·지적·처분이 바뀌었습니다. 수정에 보낼 입력을 다시 확인하세요.')
            if self.store.row('SELECT 1 FROM answer_revisions WHERE revision_id = ?', revision_id):
                raise ControllerError('이미 시작한 수정입니다. 같은 확인으로 다시 부르지 않습니다.')
            self.invocations._upper_call_gate('수정은')
            spec = ParticipantSpec(**prepared['author'])
            # Recheck and materialize the same fixed source copy as the original run.
            _, folder = self.inputs._attempt_input(run_id, pid)

            def insert(tx, attempt, kind):
                tx.execute('INSERT INTO answer_revisions (revision_id,run_id,pid,parent_id,created_at,author,snapshot,'
                           'snapshot_sha256,prompt,input_sha256,attempt,kind,state) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                           revision_id, run_id, pid, prepared['parent_id'], time.time(), format_.encoded(prepared['author']),
                           format_.encoded(prepared['snapshot']), prepared['snapshot_sha256'], prepared['prompt'],
                           prepared['input_sha256'], attempt, kind, RUNNING)

            self.execution._start_seat(REVISION_SEAT, run_id, {'revision_id': revision_id}, spec, prepared['prompt'],
                os.path.join(self.runtime.work_root, run_id, revision_id), insert, inputs=(folder,) if folder else ())
            return revision_id

    def recheck(self, revision_id, reviewer_pid):
        with self.runtime.lock:
            if self.runtime.closing:
                raise ControllerError('controller is shutting down')
            row = self.store.row('SELECT * FROM answer_revisions WHERE revision_id = ?', revision_id)
            if row is None:
                raise ControllerError('수정 판을 찾을 수 없습니다.')
            reply = self._answer(row)
            snapshot = json.loads(row['snapshot'])
            if format_.digest(format_.encoded(snapshot)) != row['snapshot_sha256']:
                raise ControllerError('수정 근거의 해시가 맞지 않습니다.')
            part = self.repository._part(row['run_id'], reviewer_pid)
            spec = ParticipantSpec(**json.loads(part['spec']))
            if reviewer_pid == row['pid'] or part['state'] != ACCEPTED or spec.transport != CLI:
                raise ControllerError('원래 답을 낸 다른 CLI 팀원을 재검토자로 고르세요.')
            gate = self.repository._gate(row['run_id'])
            if not (gate.collected if gate.general else gate.revealed) or format_.general(snapshot) != gate.general:
                raise ControllerError('공개된 격리 실행이나 모두 끝난 일반 실행의 수정 답만 재검토합니다.')
            if gate.general and self.repository._run(row['run_id'])['cancel_requested']:
                raise ControllerError('취소한 실행의 수정 답은 재검토하지 않습니다.')
            self.invocations._cli_card(spec, '수정 재검토자')
            previous = self.store.rows('SELECT state FROM revision_checks WHERE revision_id = ?', revision_id)
            if any(r['state'] in (RUNNING, UNKNOWN) for r in previous):
                raise ControllerError('앞선 재검토 호출의 종료를 먼저 확인하세요.')
            if len(previous) >= format_.MAX_CHECKS:
                raise ControllerError(f'수정 판 하나의 재검토는 {format_.MAX_CHECKS}번까지입니다. 실패도 포함합니다.')
            self.invocations._upper_call_gate('재검토는')
            key = 'rc-' + uuid.uuid4().hex
            text = format_.recheck_prompt(snapshot, reply['answer'])

            def insert(tx, attempt, kind):
                tx.execute('INSERT INTO revision_checks (check_id,revision_id,run_id,created_at,reviewer,snapshot,'
                           'answer,answer_sha256,prompt,input_sha256,attempt,kind,state) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                           key, revision_id, row['run_id'], time.time(), format_.encoded(asdict(spec)),
                           row['snapshot'], reply['answer'], reply['sha256'], text, format_.digest(text), attempt, kind, RUNNING)

            self.execution._start_seat(RECHECK_SEAT, row['run_id'], {'check_id': key}, spec, text,
                                       os.path.join(self.runtime.work_root, row['run_id'], key), insert)
            return key

    def acknowledge(self, key, *, recheck=False):
        seat = RECHECK_SEAT if recheck else REVISION_SEAT
        row = self.store.row(f'SELECT run_id FROM {seat.table} WHERE {seat.match}', key)
        if row is None:
            raise ControllerError('호출을 찾을 수 없습니다.')
        self.execution._acknowledge_seat(seat, row['run_id'], {seat.keys[0]: key})
