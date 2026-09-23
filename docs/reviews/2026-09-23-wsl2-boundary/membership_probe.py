"""Pure-function quorum probe. No CLI, network, or model calls."""
import sys, pathlib, hashlib, json
BASE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'snapshot'))
from core import membership as m
b = pathlib.Path(m.__file__).read_bytes()
sha = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
assert sha == '18f41b565a071bd8764132f7684bdbb2ffa224d9', sha
r = m.start(('A', 'B', 'C'), min_independent=3, alternates=('D',))
observed = []
for event, participant in [('unavailable', 'A'), ('unavailable', 'B'), ('substitute_requested', 'D')]:
    decision = m.decide(r, event, participant)
    r = decision.roster
    observed.append(dict(event=event, participant=participant, action=decision.action,
                         active=sorted(r.active), counted=len(r.active-r.unknown),
                         min_independent=r.min_independent))
result = dict(module_git_blob=sha, model_calls=0, sequence=observed,
              phase_skip=m.advance(m.start(('A','B'), min_independent=2), m.SYNTHESIS).phase)
(BASE / 'results').mkdir(exist_ok=True)
(BASE / 'results' / 'membership-probe-results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
