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
                    observed_at=self.now, now=self.now)}

    def test_reads_never_query_and_repeat_refreshes_are_coalesced(self):
        self.assertIsNone(self.quota.view()['quota'])
        self.reader.assert_not_called()
        self.quota.refresh()
        for _ in range(5):
            self.quota.view()
            self.quota.refresh()
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
