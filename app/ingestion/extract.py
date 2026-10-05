"""Source preparation boundary: conversion is explicit, bounded and model-free."""
import base64
from email.message import Message
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import threading

from core import runner
from app.domain import ControllerError
from app.source_document import document, digest

MAX_INPUT = 1024 * 1024
_slot = threading.BoundedSemaphore(1)


def _command(argv, directory, *, stdin=None, limit=1024 * 1024, timeout=6, json_error=False):
    result = runner.run(argv, cwd=directory, env={**os.environ, 'LC_ALL': 'C'}, timeout=timeout,
                        stdin_text=stdin, max_output_bytes=limit)
    if result.state != runner.EXITED or result.exit_code != 0 or result.stdout_truncated or result.stderr_truncated:
        if json_error and result.state == runner.EXITED and not result.stdout_truncated:
            try:
                message = json.loads(result.stdout)['error']
            except (ValueError, KeyError, TypeError):
                message = None
            if isinstance(message, str) and len(message) <= 300:
                raise ControllerError(message)
        raise ControllerError('자료 변환에 실패했거나 시간·출력 상한을 넘겼습니다. 원본은 첨부되지 않았습니다.')
    return result.stdout


class _HTML(HTMLParser):
    ignored = {'head', 'script', 'style', 'noscript', 'template', 'svg'}
    void = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
    blocks = {'p', 'div', 'section', 'article', 'main', 'header', 'footer', 'nav', 'li', 'br', 'tr', 'h1', 'h2', 'h3', 'h4', 'pre'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden, self.parts, self.omitted = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag == 'body' and 'head' in self.hidden:
            self.hidden.clear()  # HTML permits an omitted closing head tag.
        attrs = dict(attrs)
        hide = tag in self.ignored or 'hidden' in attrs or attrs.get('aria-hidden') == 'true'
        if self.hidden or hide:
            if tag not in self.void:
                self.hidden.append(tag)
            if hide:
                self.omitted += 1
        elif tag in self.blocks:
            self.parts.append('\n')
        elif tag in ('td', 'th'):
            self.parts.append('\t')

    def handle_endtag(self, tag):
        if tag in self.hidden:
            at = len(self.hidden) - 1 - self.hidden[::-1].index(tag)
            del self.hidden[at:]
        elif not self.hidden and tag in self.blocks:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

    def text(self):
        return '\n'.join(line.strip() for line in ''.join(self.parts).splitlines() if line.strip())


def from_url(body):
    url = body.get('url')
    if not isinstance(url, str) or len(url) > 2000:
        raise ControllerError('URL은 2000자 이하의 글이어야 합니다.')
    with tempfile.TemporaryDirectory(prefix='decision-url-') as tmp:
        output = _command([sys.executable, '-I', str(Path(__file__).with_name('url_fetch.py'))], tmp,
                          stdin=json.dumps({'url': url}), limit=2 * MAX_INPUT, timeout=8, json_error=True)
    fetched = json.loads(output)
    raw = base64.b64decode(fetched['body'], validate=True)
    if len(raw) > MAX_INPUT:
        raise ControllerError('자료가 1 MiB를 넘었습니다.')
    message = Message(); message['content-type'] = fetched['content_type']
    mime, charset = message.get_content_type(), message.get_content_charset() or 'utf-8'
    if mime not in ('text/html', 'text/plain', 'text/markdown', 'text/csv', 'application/json', 'application/xhtml+xml'):
        raise ControllerError('이 URL은 지원하는 글 형식이 아닙니다. PDF는 파일로 골라 주세요.')
    try:
        text = raw.decode(charset, errors='strict').lstrip('\ufeff')
        if not isinstance(text, str):
            raise ValueError('not a text codec')
    except (LookupError, ValueError, TypeError):
        raise ControllerError('문자 인코딩을 읽지 못했습니다. UTF-8 텍스트 파일로 변환해 주세요.') from None
    omissions = ['브라우저 스크립트·외부 자료·이미지는 읽지 않음', '로그인·쿠키 없이 받은 응답이며 동적 화면과 다를 수 있음']
    skipped = 0
    if mime in ('text/html', 'application/xhtml+xml'):
        parser = _HTML(); parser.feed(text); parser.close(); text = parser.text(); skipped = parser.omitted
        omissions += ['head·script·style·noscript·template·svg·hidden 영역 제외', 'CSS 배치·표 구조·링크 주소는 재현하지 않음']
    meta = {'kind': 'url', 'origin': url, 'final_url': fetched['url'], 'redirect_chain': fetched['redirect_chain'],
            'original_sha256': digest(raw), 'original_bytes': len(raw), 'content_type': mime, 'charset': charset,
            'tool': 'stdlib HTMLParser/decoded-text', 'omissions': omissions, 'omitted_elements': skipped}
    return document(text, meta, body.get('first_line', 1), body.get('last_line'))


def from_pdf(body):
    name, data = body.get('name'), body.get('data')
    if not isinstance(name, str) or not 1 <= len(name) <= 200 or not isinstance(data, str) or len(data) > (MAX_INPUT + 2) // 3 * 4:
        raise ControllerError('PDF 이름과 1 MiB 이하의 파일이 필요합니다.')
    try:
        raw = base64.b64decode(data, validate=True)
    except ValueError:
        raise ControllerError('PDF 파일 인코딩이 잘못됐습니다.') from None
    if not raw.startswith(b'%PDF-') or len(raw) > MAX_INPUT:
        raise ControllerError('1 MiB 이하의 PDF 파일만 받습니다.')
    info, convert = shutil.which('pdfinfo'), shutil.which('pdftotext')
    if not info or not convert:
        raise ControllerError('이 서버에 Poppler의 pdfinfo·pdftotext가 필요합니다. 설치 후 다시 추출하거나 텍스트 파일을 첨부하세요.')
    with tempfile.TemporaryDirectory(prefix='decision-pdf-') as tmp:
        path = Path(tmp) / 'source.pdf'; path.write_bytes(raw)
        details = _command([info, str(path)], tmp, limit=65536, timeout=4)
        found = re.search(r'^Pages:\s+(\d+)\s*$', details, re.M)
        if not found:
            raise ControllerError('PDF 페이지 수를 확인할 수 없습니다.')
        total = int(found[1]); first = body.get('first_page', 1); last = body.get('last_page')
        last = min(total, first + 19) if last is None and type(first) is int else last
        if type(first) is not int or type(last) is not int or not 1 <= first <= last <= total or last - first >= 20:
            raise ControllerError(f'페이지는 1~{total} 사이에서 한 번에 20쪽까지 고릅니다.')
        text = _command([convert, '-f', str(first), '-l', str(last), '-enc', 'UTF-8', '-layout', str(path), '-'], tmp)
    pages = text.split('\f')
    if pages and not pages[-1].strip():
        pages.pop()
    if len(pages) != last - first + 1:
        raise ControllerError('변환된 페이지 경계를 확인할 수 없습니다.')
    empty = [first + i for i, page in enumerate(pages) if not page.strip()]
    if len(empty) == len(pages):
        raise ControllerError('고른 페이지에서 글을 추출하지 못했습니다. 스캔 PDF는 OCR이 필요합니다.')
    text = '\n\n'.join(f'[PDF page {first + i}]\n{page.strip()}' for i, page in enumerate(pages))
    meta = {'kind': 'pdf', 'origin': name, 'original_sha256': digest(raw), 'original_bytes': len(raw),
            'tool': 'Poppler pdfinfo/pdftotext -layout UTF-8', 'pages': {'first': first, 'last': last, 'total': total},
            'omitted_pages': total - (last - first + 1), 'pages_without_text': empty,
            'omissions': ['이미지·스캔 OCR·주석·첨부 파일은 추출하지 않음', '글 순서·표 배치·수식이 원본과 다를 수 있음']}
    return document(text, meta, body.get('first_line', 1), body.get('last_line'))


def extract(body):
    if not isinstance(body, dict) or body.get('kind') not in ('pdf', 'url'):
        raise ControllerError('PDF 또는 URL 추출을 고르세요.')
    if not _slot.acquire(blocking=False):
        raise ControllerError('다른 자료를 추출 중입니다. 끝난 뒤 다시 시도하세요.')
    try:
        result = from_pdf(body) if body['kind'] == 'pdf' else from_url(body)
        # The returned self-contained text already carries its immutable metadata.
        return result
    finally:
        _slot.release()
