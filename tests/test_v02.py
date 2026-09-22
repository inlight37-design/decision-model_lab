"""합성 fixture에 대한 순수 데이터 계약 검사; 실제 프로세스/권한 검증 아님."""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_v02 import fingerprint, strict_load, validate_plan, validate_proof

# validate_v02 는 jsonschema 를 함수 안에서 import 하므로 이 모듈은 의존성 없이도 읽힌다.
# 그러나 schema 검사에 의존하는 test 는 설치 없이 실행하면 ModuleNotFoundError 로 터진다.
# 없는 의존성을 실패가 아니라 skip 으로 표시한다. 미설치와 계약 위반은 다른 상태다.
try:
    import jsonschema  # noqa: F401
    HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover - 환경에 따라 달라진다
    HAS_JSONSCHEMA = False

NEEDS_JSONSCHEMA = unittest.skipUnless(
    HAS_JSONSCHEMA,
    "jsonschema 미설치: python -m pip install -r requirements-design.txt",
)


class Fixtures(unittest.TestCase):
    """합성 fixture 로딩만 담당한다. 로딩 자체는 표준 라이브러리로 충분하다."""

    def setUp(self) -> None:
        self.plan = strict_load(ROOT / "examples/v0.2/pilot.json")
        fixture = strict_load(ROOT / "examples/v0.2/proof-fixture.json")
        self.expected, self.proof = fixture["expected"], fixture["proof"]

    def proof_errors(self) -> list[str]:
        return validate_proof(self.plan, self.expected, self.proof)


class SerializationAndParsing(Fixtures):
    """schema 없이도 성립해야 하는 순수 데이터 불변 조건."""

    def test_stable_serialization(self):
        reordered = dict(reversed(list(copy.deepcopy(self.plan).items())))
        self.assertEqual(fingerprint(self.plan), fingerprint(reordered))

    def test_duplicate_json_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                strict_load(path)


@NEEDS_JSONSCHEMA
class DesignContracts(Fixtures):
    """plan/proof 의 schema 결합 검사. jsonschema 가 필요하다."""

    def test_valid_offline_fixture(self):
        self.assertEqual(self.proof_errors(), [])

    def test_competing_state_authorities(self):
        self.plan["state_authorities"] = ["task_manifest", "tracker"]
        self.assertTrue(validate_plan(self.plan))

    def test_automatic_merge(self):
        self.plan["worker"]["automatic_merge"] = True
        self.assertTrue(validate_plan(self.plan))

    def test_unbounded_attempts(self):
        self.plan["worker"]["max_attempts"] = 0
        self.assertTrue(validate_plan(self.plan))

    def test_more_than_two_workers(self):
        self.plan["worker"]["max_parallel"] = 3
        self.assertTrue(validate_plan(self.plan))

    def test_per_turn_judge_is_not_a_default_event(self):
        self.plan["routing"]["decision_points"] = ["every_turn"]
        self.assertTrue(validate_plan(self.plan))

    def test_uncertainty_is_not_cheap_fallback(self):
        self.plan["routing"]["uncertainty_action"] = "cheap"
        self.assertTrue(validate_plan(self.plan))

    def test_remote_context_needs_approval(self):
        self.plan["context"]["mode"] = "relevance_remote"
        self.assertTrue(validate_plan(self.plan))

    def test_jev_shadow_needs_approval(self):
        self.plan["routing"]["advisory"] = "jev_shadow"
        self.assertTrue(validate_plan(self.plan))

    def test_approved_shadow_is_only_a_valid_design(self):
        self.plan["routing"]["advisory"] = "jev_shadow"
        self.plan["context"]["remote_approved"] = True
        self.assertEqual(validate_plan(self.plan), [])

    def test_raw_recovery_cannot_disappear(self):
        self.plan["context"]["expand_available"] = False
        self.assertTrue(validate_plan(self.plan))

    def test_selector_ownership_conflict(self):
        self.plan["routing"]["primary"] = "switchyard"
        self.assertTrue(validate_plan(self.plan))

    def test_switchyard_is_sole_gateway_selector(self):
        self.plan["routing"]["primary"] = "switchyard"
        self.plan["routing"]["model_selection_owner"] = "gateway"
        self.assertEqual(validate_plan(self.plan), [])

    def test_observed_cost_is_not_hard_cap(self):
        self.plan["measurement"]["usd_cap"] = 1.0
        self.assertTrue(validate_plan(self.plan))

    def test_worker_cannot_issue_trusted_proof(self):
        self.proof["verifier_id"] = "worker"
        self.assertTrue(self.proof_errors())

    def test_candidate_binding(self):
        self.proof["candidate_sha256"] = "5" * 64
        self.assertTrue(self.proof_errors())

    def test_base_binding(self):
        self.proof["base_commit"] = "6" * 40
        self.assertTrue(self.proof_errors())

    def test_acceptance_binding(self):
        self.proof["acceptance_sha256"] = "7" * 64
        self.assertTrue(self.proof_errors())

    def test_stale_policy(self):
        self.plan["worker"]["max_attempts"] = 1
        self.assertEqual(validate_plan(self.plan), [])
        self.assertTrue(self.proof_errors())

    def test_partial_is_not_passed(self):
        self.proof["status"] = "partial"
        self.assertTrue(self.proof_errors())

    def test_missing_regression(self):
        del self.proof["checks"]["regression"]
        self.assertTrue(self.proof_errors())

    def test_failed_extra_check_is_not_hidden(self):
        self.proof["checks"]["new_scenario"] = "failed"
        self.assertTrue(self.proof_errors())

    def test_unhealthy_baseline(self):
        self.proof["baseline_passed"] = False
        self.assertTrue(self.proof_errors())

    def test_unknown_cost_not_zero(self):
        self.proof["usage"]["total_usd"] = 0.0
        self.assertTrue(self.proof_errors())

    def test_measured_cost_requires_value(self):
        self.proof["usage"]["status"] = "measured"
        self.assertTrue(self.proof_errors())

    def test_nonfinite_cost(self):
        self.proof["usage"] = {"status": "measured", "total_usd": float("nan")}
        self.assertTrue(self.proof_errors())


if __name__ == "__main__":
    unittest.main()
