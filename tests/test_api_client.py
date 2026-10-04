"""Actual browser transport helpers: no server, model or network."""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'), 'Node required')
class RequestOwnershipTests(unittest.TestCase):
    def test_auth_stays_local_and_superseded_reads_cannot_claim_current_state(self):
        source = (Path(__file__).resolve().parents[1] / 'app/static/api.js').read_text(encoding='utf-8')
        program = source + r'''
const assert = require('node:assert/strict');
(async () => {
  const calls = [];
  const api = createAPI('synthetic-token', async (path, options) => {
    calls.push([path, options]);
    return {ok:true, json:async()=>({answer:'public'})};
  });
  assert.deepEqual(await api('/api/state'), {answer:'public'});
  assert.equal(calls[0][1].headers.Authorization, 'Bearer synthetic-token');
  assert.equal(calls[0][1].redirect, 'error');
  assert.equal(calls[0][1].method, 'GET');
  await api('/api/runs', {});
  assert.equal(calls[1][1].method, 'POST');
  for (const path of ['https://outside.invalid/api/', '//outside.invalid/api/', '/api/\\outside']) {
    await assert.rejects(api(path));
  }
  assert.equal(calls.length, 2);
  const owner = new LatestRequest(), first = owner.begin(), second = owner.begin();
  assert.equal(first.signal.aborted, true);
  assert.equal(first.current(), false);
  assert.equal(second.current(), true);
  owner.cancel();
  assert.equal(second.current(), false);
  assert.equal(second.signal.aborted, true);
  const bad = createAPI('synthetic-token', async()=>({ok:false,status:409,json:async()=>({error:'blocked'})}));
  await assert.rejects(bad('/api/state'), /blocked/);
})().catch(error => { console.error(error); process.exitCode=1; });
'''
        result = subprocess.run(['node', '-e', program], capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
