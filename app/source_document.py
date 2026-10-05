"""Self-contained extracted text; provenance travels with templates and source snapshots."""
import hashlib
import json
import re
from datetime import datetime, timezone
from app.domain import ControllerError, storable

PREFIX = 'DECISION-SOURCE/1\n'
SEPARATOR = '\n--- EXTRACTED TEXT ---\n'
MAX_TEXT = 190 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def document(text, provenance, first=1, last=None):
    if not isinstance(text, str) or not storable(text) or '\x00' in text:
        raise ControllerError('추출 결과가 올바른 UTF-8 글이 아닙니다.')
    text = text.replace('\r\n', '\n').replace('\r', '\n').strip()
    if not text:
        raise ControllerError('추출한 글이 없습니다. 스캔·이미지·동적 페이지는 별도 변환이 필요합니다.')
    lines = text.split('\n')
    last = min(len(lines), first + 999) if last is None and type(first) is int else last
    if type(first) is not int or type(last) is not int or not 1 <= first <= last <= len(lines):
        raise ControllerError(f'추출 글의 줄 범위는 1~{len(lines)} 안에서 고릅니다.')
    selected = '\n'.join(lines[first - 1:last])
    raw = selected.encode('utf-8')
    if len(raw) > MAX_TEXT:
        raise ControllerError('고른 글이 너무 큽니다. 페이지나 줄 범위를 줄이세요(190 KiB까지).')
    if not selected.strip():
        raise ControllerError('고른 범위에 글이 없습니다.')
    meta = {**provenance, 'extracted_at': datetime.now(timezone.utc).isoformat(),
            'format': 'decision-source/1', 'converted_sha256': digest(text.encode('utf-8')),
            'selected_sha256': digest(raw), 'selected_bytes': len(raw),
            'lines': {'first': first, 'last': last, 'total': len(lines)},
            'omitted_lines': len(lines) - (last - first + 1),
            'authenticity': 'not_verified', 'original_bytes_retained': False}
    meta['metadata_sha256'] = digest(encoded(meta).encode('utf-8'))
    if len(encoded(meta).encode('utf-8')) > 32000:
        raise ControllerError('출처 정보가 너무 큽니다. 더 짧은 URL을 사용하세요.')
    result = PREFIX + encoded(meta) + SEPARATOR + selected
    return {'text': result, 'preview': selected, 'provenance': meta, 'sha256': digest(result.encode('utf-8')),
            'bytes': len(result.encode('utf-8')), 'model_calls': 0}


def metadata(content, *, header_only=False):
    """Checksums detect accidental edits, not authorship or original-source truth."""
    if not content.startswith(PREFIX.encode('utf-8')):
        return None
    try:
        header, body = content.decode('utf-8')[len(PREFIX):].split(SEPARATOR, 1)
        if len(header.encode('utf-8')) > 32000:
            raise ValueError('large metadata')
        meta = json.loads(header)
        if not isinstance(meta, dict) or meta.get('format') != 'decision-source/1':
            raise ValueError('format')
        if (meta.get('kind') not in ('pdf', 'url') or not isinstance(meta.get('origin'), str) or
                not 1 <= len(meta['origin']) <= 2000 or type(meta.get('selected_bytes')) is not int or
                not 0 < meta['selected_bytes'] <= MAX_TEXT or
                not isinstance(meta.get('omissions'), list) or
                any(not isinstance(s, str) or len(s) > 1000 for s in meta['omissions'])):
            raise ValueError('provenance fields')
        for key in ('original_sha256', 'converted_sha256', 'selected_sha256', 'metadata_sha256'):
            if not isinstance(meta.get(key), str) or not re.fullmatch('[0-9a-f]{64}', meta[key]):
                raise ValueError('digest format')
        for key in ('lines', 'pages') if meta['kind'] == 'pdf' else ('lines',):
            span = meta[key]
            if (not isinstance(span, dict) or any(type(span.get(k)) is not int for k in ('first', 'last', 'total')) or
                    not 1 <= span['first'] <= span['last'] <= span['total']):
                raise ValueError('range')
        other = {k: v for k, v in meta.items() if k != 'metadata_sha256'}
        if (digest(encoded(other).encode('utf-8')) != meta.get('metadata_sha256') or
                not header_only and (digest(body.encode('utf-8')) != meta.get('selected_sha256') or
                                     len(body.encode('utf-8')) != meta.get('selected_bytes'))):
            raise ValueError('digest')
        return meta
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise ControllerError('추출 자료의 출처 기록이나 글이 바뀌었습니다. 다시 추출해 확인하세요.') from None


def listing(name, content, *, assignment=False):
    item = {'name': name, 'sha256': digest(content), 'bytes': len(content)}
    meta = metadata(content)
    if meta is not None:
        item.update(kind='extracted', range='selected', provenance=meta)
    elif assignment:
        item.update(kind='original', range='whole')
    return item
