"""Offline PDF/HTML fixtures, bounded public fetch and provenance across the work flow."""
import base64
import copy
import http.client
import json
import os
import shutil
import socket
import unittest
from unittest.mock import patch, Mock

from app import controller as c, source_document as doc
from app.ingestion import extract as ingestion, url_fetch
from app.report import build_report
from test_app_controller import Base, SyntheticExecutor
from test_app_integrity import HttpServerCase
from test_templates import draft, ROSTER
from test_sources import Recording


def pdf_fixture(empty=False):
    """Small valid two-page PDF, generated without a Python dependency."""
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for text in (b'' if empty else b'First page counterexample', b'Second page condition' if not empty else b''):
        stream = b'BT /F1 12 Tf 72 720 Td (' + text + b') Tj ET'
        objects.append(b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream')
    result = b'%PDF-1.4\n'; offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(result)); result += str(i).encode() + b' 0 obj\n' + obj + b'\nendobj\n'
    start = len(result)
    result += b'xref\n0 8\n0000000000 65535 f \n'
    for offset in offsets[1:]: result += f'{offset:010d} 00000 n \n'.encode()
    return result + b'trailer\n<< /Size 8 /Root 1 0 R >>\nstartxref\n' + str(start).encode() + b'\n%%EOF\n'


def fetched(raw=b'<html><head><title>title</title></head><body><h1>Heading</h1><p>first</p><script>HIDDEN</script><p>second</p></body></html>', mime='text/html; charset=utf-8'):
    return json.dumps({'body': base64.b64encode(raw).decode(), 'url': 'https://example.com/final',
                       'redirect_chain': ['https://example.com/', 'https://example.com/final'], 'content_type': mime})


def extracted():
    with patch.object(ingestion, '_command', return_value=fetched()):
        return ingestion.extract({'kind': 'url', 'url': 'https://example.com/', 'first_line': 2, 'last_line': 3})


class Extraction(unittest.TestCase):
    def test_html_selection_omissions_and_hashes_are_part_of_the_source(self):
        result = extracted(); meta = result['provenance']
        self.assertEqual(result['preview'], 'first\nsecond')
        self.assertNotIn('HIDDEN', result['text'])
        self.assertEqual(meta['lines'], {'first': 2, 'last': 3, 'total': 3})
        self.assertEqual(meta['omitted_lines'], 1)
        self.assertEqual(doc.metadata(result['text'].encode()), meta)
        self.assertFalse(meta['original_bytes_retained'])
        for bad in (result['text'] + 'changed', result['text'].replace('https://example.com/', 'https://other.com/')):
            with self.assertRaises(c.ControllerError): doc.metadata(bad.encode())
        with patch.object(ingestion, '_command', return_value=fetched(b'<head><title>x</title><body><p>visible</p>')):
            self.assertEqual(ingestion.extract({'kind': 'url', 'url': 'https://example.com'})['preview'], 'visible')

    def test_unsupported_encoding_empty_binary_oversize_and_bad_selection_fail(self):
        for raw, mime in ((b'\xff', 'text/plain; charset=utf-8'), (b'abc', 'image/png'),
                          (b'<script>only script</script>', 'text/html'), (b'\x00', 'text/plain'),
                          (b'x' * (ingestion.MAX_INPUT + 1), 'text/plain')):
            with self.subTest(mime=mime), patch.object(ingestion, '_command', return_value=fetched(raw, mime)), self.assertRaises(c.ControllerError):
                ingestion.extract({'kind': 'url', 'url': 'https://example.com'})
        for first, last in ((0, 1), (2, 1), (True, 3), (1, 4)):
            with patch.object(ingestion, '_command', return_value=fetched()), self.assertRaises(c.ControllerError):
                ingestion.extract({'kind': 'url', 'url': 'https://example.com', 'first_line': first, 'last_line': last})
        with self.assertRaises(c.ControllerError):
            doc.document('x' * (doc.MAX_TEXT + 1), {})

    def test_pdf_real_page_selection_and_empty_scanned_failure(self):
        available = shutil.which('pdfinfo') and shutil.which('pdftotext')
        if not available:
            if os.environ.get('DML_REQUIRE_POPPLER') == '1': self.fail('Poppler required in this CI job')
            self.skipTest('Poppler not installed; optional PDF converter not observed here')
        raw = pdf_fixture()
        body = {'kind': 'pdf', 'name': 'two.pdf', 'data': base64.b64encode(raw).decode(), 'first_page': 2, 'last_page': 2}
        result = ingestion.extract(body)
        self.assertIn('Second page condition', result['preview']); self.assertNotIn('First page', result['preview'])
        self.assertEqual(result['provenance']['pages'], {'first': 2, 'last': 2, 'total': 2})
        self.assertEqual(result['provenance']['omitted_pages'], 1)
        self.assertEqual(result['provenance']['original_sha256'], doc.digest(raw))
        with self.assertRaises(c.ControllerError): ingestion.extract({**body, 'last_page': 3})
        with self.assertRaises(c.ControllerError): ingestion.extract({**body, 'data': base64.b64encode(pdf_fixture(True)).decode()})

    def test_missing_converter_invalid_pdf_and_busy_extract_do_not_make_sources(self):
        body = {'kind': 'pdf', 'name': 'file.pdf', 'data': base64.b64encode(pdf_fixture()).decode()}
        with patch.object(ingestion.shutil, 'which', return_value=None), self.assertRaisesRegex(c.ControllerError, 'Poppler'):
            ingestion.extract(body)
        for data in ('invalid!!', base64.b64encode(b'not a PDF').decode()):
            with self.assertRaises(c.ControllerError): ingestion.extract({**body, 'data': data})
        with ingestion._slot:
            with self.assertRaisesRegex(c.ControllerError, '추출 중'): ingestion.extract(body)


class PublicFetch(unittest.TestCase):
    def addresses(self, *ips):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443)) for ip in ips]

    def test_private_mixed_credentials_scheme_ports_and_control_characters_are_rejected(self):
        for ip in ('127.0.0.1', '10.0.0.1', '169.254.169.254', '::1', '100.64.0.1', '224.0.0.1'):
            with patch.object(url_fetch.socket, 'getaddrinfo', return_value=self.addresses(ip)), self.assertRaises(ValueError):
                url_fetch.target('https://example.com')
        with patch.object(url_fetch.socket, 'getaddrinfo', return_value=self.addresses('93.184.216.34', '10.0.0.2')), self.assertRaises(ValueError):
            url_fetch.target('https://example.com')
        for url in ('file:///etc/passwd', 'ftp://example.com', 'https://user:secret@example.com', 'https://example.com:8080',
                    'https://example.com/\nHeader:bad', 'https://example.com\\@localhost'):
            with self.assertRaises(ValueError): url_fetch.target(url)

    def test_proxy_connect_uses_vetted_ip_and_tls_uses_original_hostname(self):
        conn = Mock(); ctx = Mock()
        with patch.object(url_fetch, 'getproxies', return_value={'https': 'http://proxy.test:8080'}), \
             patch.object(url_fetch, 'proxy_bypass', return_value=False), \
             patch.object(url_fetch.http.client, 'HTTPConnection', return_value=conn) as factory, \
             patch.object(url_fetch.ssl, 'create_default_context', return_value=ctx):
            self.assertIs(url_fetch.connection('https', 'example.com', 443, '93.184.216.34', 5), conn)
            factory.assert_called_once_with('proxy.test', 8080, timeout=5)
            conn.set_tunnel.assert_called_once_with('93.184.216.34', 443)
            self.assertEqual(ctx.wrap_socket.call_args.kwargs['server_hostname'], 'example.com')
        with patch.object(url_fetch, 'getproxies', return_value={'https': 'socks5://proxy.test:8080'}), \
             patch.object(url_fetch, 'proxy_bypass', return_value=False), self.assertRaises(ValueError):
            url_fetch.connection('https', 'example.com', 443, '93.184.216.34', 5)

    def test_redirect_revalidates_and_does_not_contact_private_target(self):
        response = Mock(status=302); response.getheader.return_value = 'http://127.0.0.1/'
        conn = Mock(); conn.getresponse.return_value = response
        with patch.object(url_fetch.socket, 'getaddrinfo', side_effect=[self.addresses('93.184.216.34'), self.addresses('127.0.0.1')]), \
             patch.object(url_fetch, 'connection', return_value=conn) as connect, self.assertRaises(ValueError):
            url_fetch.fetch('https://example.com')
        self.assertEqual(connect.call_count, 1); conn.close.assert_called_once()

    def test_size_compression_partial_and_redirect_limits_never_return_partial_success(self):
        for headers, chunks in (({'Content-Length': str(url_fetch.MAX_BYTES + 1)}, []),
                                ({'Content-Encoding': 'gzip'}, []), ({'Content-Length': '4'}, [b'a', b'']),
                                ({}, [b'x' * (url_fetch.MAX_BYTES + 1)])):
            response = Mock(status=200); response.getheader.side_effect = lambda key, default=None: headers.get(key, default)
            response.read.side_effect = chunks
            conn = Mock(); conn.getresponse.return_value = response
            with patch.object(url_fetch.socket, 'getaddrinfo', return_value=self.addresses('93.184.216.34')), \
                 patch.object(url_fetch, 'connection', return_value=conn), self.assertRaises(ValueError): url_fetch.fetch('https://example.com')
            conn.close.assert_called_once()
        response = Mock(status=302); response.getheader.return_value = '/again'
        conn = Mock(); conn.getresponse.return_value = response
        with patch.object(url_fetch.socket, 'getaddrinfo', return_value=self.addresses('93.184.216.34')), \
             patch.object(url_fetch, 'connection', return_value=conn) as connect, self.assertRaises(ValueError): url_fetch.fetch('https://example.com')
        self.assertEqual(connect.call_count, 4)


class SourceJourney(Base):
    def test_provenance_survives_template_preview_confirm_report_search_and_general_delivery(self):
        ctl = self.controller(Recording()); result = extracted()
        data = draft(); data['sources'] = [{'name': 'url.txt', 'text': result['text']}]
        saved = ctl.templates.save('출처 보관', data, ROSTER); restored = ctl.templates.load(saved['template_id'])
        self.assertEqual(restored['sources'][0]['provenance'], result['provenance'])
        args = {'min_independent': 1, 'sources': [('url.txt', result['text'])]}
        preview = ctl.prepare_run('출처 확인', [ROSTER['claude']], **args)
        self.assertEqual(preview['sources'][0]['kind'], 'extracted')
        rid = ctl.create_run('출처 확인', [ROSTER['claude']], run_id=preview['run_id'], confirmation=preview['confirmation'], **args)
        self.assertTrue(ctl.wait_idle())
        view = self.run_view(ctl, rid); self.assertEqual(view['sources'], preview['sources'])
        report = build_report(ctl.view(), rid); self.assertEqual(report['schema'], 'a1-draft-report/6')
        self.assertEqual(report['input']['sources'][0]['provenance'], result['provenance'])
        ctl.synthesize(rid)
        self.assertEqual(self.run_view(ctl, rid)['synthesis']['status'], 'completed')
        self.assertEqual(ctl.search('example.com', kind='source')['total'], 1)
        self.assertEqual(ctl.queries.source(rid, 'url.txt')['text'], result['text'])
        args.update(role_board={**data['role_board'], 'isolated': [], 'general': ['claude']}, roster=ROSTER,
                    assignments={'claude': {'task': '자료 확인', 'sources': ['url.txt']}})
        general = ctl.create_run('출처 확인', [ROSTER['claude']], **args); self.assertTrue(ctl.wait_idle())
        self.assertEqual(self.part(ctl, general, 'claude')['state'], c.ACCEPTED)
        self.assertEqual(self.part(ctl, general, 'claude')['assignment']['sources'][0]['kind'], 'extracted')
        with self.assertRaises(c.ControllerError):
            ctl.templates.save('변조', {**data, 'sources': [{'name': 'url.txt', 'text': result['text'] + 'changed'}]}, ROSTER)


class ExtractionHTTP(HttpServerCase):
    def test_extraction_needs_auth_and_does_not_start_or_save_a_run(self):
        body = {'kind': 'url', 'url': 'https://example.com', 'first_line': 1}
        path = '/api/sources/extract'
        self.assertEqual(self.request(body, {'Authorization': 'Bearer wrong'}, path)[0], 401)
        with patch.object(ingestion, '_command', return_value=fetched()):
            status, raw, _ = self.request(body, path=path)
        self.assertEqual(status, 200, raw)
        self.assertEqual(json.loads(raw)['provenance']['kind'], 'url')
        self.assertEqual(self.ctl.view()['runs'], [])
        self.assertEqual(self.store.row('SELECT COUNT(*) FROM sources')[0], 0)
