"""No inference: cache reads, concurrent refresh and stale/failure presentation."""
from contextlib import closing
import http.client
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import Mock

from app.account_quota import AccountQuota
from app.server import _Server, make_handler
from core.quota import claude_limit
from tools.review_boundary import quota_projection


class QuotaTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.reader = Mock(side_effect=self.report)
        self.quota = AccountQuota(Path('/ledger'), enabled=True, reader=self.reader, clock=lambda: self.now)

    def report(self, _):
        return {'tree_confirmed_empty': True, 'inference_requests_sent': 0,
                'quota': quota_projection({'rateLimits': {'primary': {
                    'usedPercent': 25, 'windowDurationMins': 300, 'resetsAt': self.now + 90}}},
                    observed_at=self.now, now=self.now),
                'models': {'status': 'observed', 'ids': ['gpt-test'], 'truncated': False}}

    def test_claude_section_only_reads_the_last_real_run_and_ages(self):
        limit = claude_limit({'status': 'allowed', 'unifiedWindows': {'five_hour': {'utilization': 0.4}}})
        calls = []

        def last_claude():
            calls.append(1)
            return {**limit, 'observed_at': 1000}
        quota = AccountQuota(Path('/ledger'), enabled=False, reader=self.reader, clock=lambda: self.now,
                             claude=last_claude)
        view = quota.view()
        self.assertTrue(view['claude']['configured'])
        self.assertEqual(view['claude']['quota']['limits'][0]['used_percent'], 40.0)
        self.assertEqual(view['claude']['quota']['status'], 'observed')
        quota.refresh()   # Codex가 없으면 조회 프로세스가 없고, Claude에는 조회 자체가 없다
        self.reader.assert_not_called()
        self.now += 121
        self.assertEqual(quota.view()['claude']['quota']['status'], 'stale')
        self.assertFalse(self.quota.view()['claude']['configured'])
        self.assertIsNone(self.quota.view()['claude']['quota'])

    def test_model_names_come_only_from_an_explicit_refresh(self):
        quota = AccountQuota(Path('/ledger'), enabled=True, reader=self.reader, clock=lambda: self.now,
                             codex_model='gpt-test')
        self.assertEqual((quota.view()['requested_model'], quota.view()['models']), ('gpt-test', None))
        self.assertEqual(quota.refresh()['models']['ids'], ['gpt-test'])

    def test_reads_never_query_and_repeat_refreshes_are_coalesced(self):
        self.assertIsNone(self.quota.view()['quota'])
        self.reader.assert_not_called()
        self.quota.refresh()
        for _ in range(5):
            self.quota.view()
            self.assertFalse(self.quota.refresh()['refreshing'])
        self.assertEqual(self.reader.call_count, 1)
        self.now += 61
        self.quota.refresh()
        self.assertEqual(self.reader.call_count, 2)

    def test_reset_expiry_age_failure_and_unknown_do_not_show_fresh_remaining(self):
        self.quota.refresh()
        original = self.quota.view()
        self.assertEqual(original['quota']['limits'][1]['status'], 'unknown')
        self.now += 91
        self.assertEqual(self.quota.view()['quota']['limits'][0]['status'], 'stale')
        self.now += 40
        self.assertEqual(self.quota.view()['quota']['freshness'], 'stale')
        self.reader.side_effect = RuntimeError('PRIVATE PROVIDER ERROR')
        failed = self.quota.refresh()
        self.assertTrue(failed['refresh_failed'])
        self.assertEqual(failed['quota']['limits'][0]['used_percent'], 25)
        self.assertNotIn('PRIVATE', json.dumps(failed))
        self.assertEqual(original['quota']['status'], 'observed')

    def test_failed_refresh_marks_a_recent_observation_stale(self):
        # 변이 M6(PR #39 병합 검토): 위 시험은 이미 120초가 지난 뒤에만 실패를 봐서 실패 표시를 가리지 못했다.
        self.quota.refresh()
        self.assertEqual(self.quota.view()['quota']['freshness'], 'fresh')
        self.now += 61   # 다시 조회할 수 있고, 옛 관측은 아직 120초가 안 됐고 초기화 전이다
        self.reader.side_effect = RuntimeError('PRIVATE PROVIDER ERROR')
        failed = self.quota.refresh()
        self.assertTrue(failed['refresh_failed'])
        self.assertEqual((failed['quota']['freshness'], failed['quota']['status']), ('stale', 'stale'))
        self.assertEqual(failed['quota']['limits'][0]['status'], 'stale')

    def test_concurrent_refresh_is_nonblocking_and_single_flight(self):
        entered, release = threading.Event(), threading.Event()
        def reader(path):
            entered.set()
            release.wait(2)
            return self.report(path)
        self.reader.side_effect = reader
        thread = threading.Thread(target=self.quota.refresh)
        thread.start()
        try:
            self.assertTrue(entered.wait(1))
            self.assertTrue(self.quota.refresh()['refreshing'])
            self.assertTrue(self.quota.view()['refreshing'])
            self.assertEqual(self.reader.call_count, 1)
        finally:
            release.set()
            thread.join(2)
        self.assertFalse(self.quota.view()['refreshing'])

    def test_disabled_or_unconfirmed_probe_never_claims_an_observation(self):
        disabled = AccountQuota(Path('/ledger'), enabled=False, reader=self.reader)
        disabled.refresh()
        self.reader.assert_not_called()
        report = self.report(None)
        report['tree_confirmed_empty'] = False
        self.reader.side_effect = None
        self.reader.return_value = report
        self.assertIsNone(self.quota.refresh()['quota'])

    def test_http_requires_auth_and_read_has_no_refresh_side_effect(self):
        controller = Mock()
        controller.executor.kind = 'real'
        server = _Server(('127.0.0.1', 0), make_handler(controller, 'token', 0))
        port = server.server_address[1]
        server.RequestHandlerClass = make_handler(controller, 'token', port, account_quota=self.quota)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def request(method, path, auth=True):
            with closing(http.client.HTTPConnection('127.0.0.1', port, timeout=2)) as conn:
                headers = {'Content-Type': 'application/json'}
                if auth:
                    headers['Authorization'] = 'Bearer token'
                conn.request(method, path, '{}' if method == 'POST' else None, headers)
                response = conn.getresponse()
                return response.status, json.loads(response.read())
        self.assertEqual(request('POST', '/api/account-quota/refresh', False)[0], 401)
        self.assertEqual(request('GET', '/api/account-quota')[0], 200)
        self.reader.assert_not_called()
        self.assertEqual(request('POST', '/api/account-quota/refresh')[1]['quota']['status'], 'observed')
        request('GET', '/api/account-quota')
        self.assertEqual(self.reader.call_count, 1)


if __name__ == '__main__':
    unittest.main()
