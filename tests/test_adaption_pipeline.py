"""
test_adaption_pipeline.py
=========================
Comprehensive test suite for adaption_pipeline.py.
Validates:
1. Credit budgeting wrapper `estimate_job_cost` across all job types.
2. Ingestion & Forge data structuring from appliance manuals and guides.
3. Invent & synthetic dataset generation with Indian consumer colloquialisms.
4. Strict local deduplication (exact hash + near-duplicate Jaccard clustering).
5. AutoScientist pilot gating (50-100 rows) and full training scaling.
6. Error handling, rate-limiting, and API key masking.
"""

import dataclasses
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

_tests_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_tests_dir)
_backend_dir = os.path.join(_root_dir, "backend")
for _p in [_root_dir, _backend_dir, _tests_dir]:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from backend.adaption_pipeline import (
        AdaptionAuthError,
        AdaptionBudgetExceededError,
        AdaptionConfig,
        AdaptionHTTPClient,
        AdaptionPilotEvaluationError,
        AdaptionRateLimitError,
        ApplianceRecord,
        deduplicate_records,
        estimate_job_cost,
        get_config,
        ingest_and_forge_manuals,
        invent_synthetic_data,
        run_appliance_pipeline,
        run_autoscientist_full_training,
        run_autoscientist_pilot,
        set_config,
    )
except ImportError:
    from adaption_pipeline import (
        AdaptionAuthError,
        AdaptionBudgetExceededError,
        AdaptionConfig,
        AdaptionHTTPClient,
        AdaptionPilotEvaluationError,
        AdaptionRateLimitError,
        ApplianceRecord,
        deduplicate_records,
        estimate_job_cost,
        get_config,
        ingest_and_forge_manuals,
        invent_synthetic_data,
        run_appliance_pipeline,
        run_autoscientist_full_training,
        run_autoscientist_pilot,
        set_config,
    )


class TestAdaptionConfigAndSecurity(unittest.TestCase):
    """Tests environment variable loading, API key validation, and masking."""

    def setUp(self):
        self.old_key = os.environ.get("ADAPTION_API_KEY")
        self.old_budget = os.environ.get("ADAPTION_CREDIT_BUDGET")
        self.old_mock = os.environ.get("ADAPTION_MOCK_MODE")

    def tearDown(self):
        if self.old_key is not None:
            os.environ["ADAPTION_API_KEY"] = self.old_key
        else:
            os.environ.pop("ADAPTION_API_KEY", None)

        if self.old_budget is not None:
            os.environ["ADAPTION_CREDIT_BUDGET"] = self.old_budget
        else:
            os.environ.pop("ADAPTION_CREDIT_BUDGET", None)

        if self.old_mock is not None:
            os.environ["ADAPTION_MOCK_MODE"] = self.old_mock
        else:
            os.environ.pop("ADAPTION_MOCK_MODE", None)

    def test_key_masking(self):
        cfg = AdaptionConfig(api_key="pt_live_998877665544332211")
        masked = cfg.get_masked_key()
        self.assertTrue(masked.startswith("pt_liv"))
        self.assertTrue(masked.endswith("2211"))
        self.assertNotIn("99887766", masked)
        self.assertNotIn("pt_live_998877665544332211", repr(cfg))

    def test_missing_key_raises_auth_error(self):
        cfg = AdaptionConfig(api_key="", mock_mode=False)
        with self.assertRaises(AdaptionAuthError):
            cfg.validate(require_key=True)

    def test_budget_parsing(self):
        os.environ["ADAPTION_CREDIT_BUDGET"] = "5000"
        cfg = AdaptionConfig(api_key="pt_test_12345678")
        self.assertEqual(cfg.credit_budget, 5000)


class TestCreditBudgeting(unittest.TestCase):
    """Tests Requirement 1: `estimate_job_cost(job_type, config)`."""

    def setUp(self):
        set_config(AdaptionConfig(api_key="pt_test_12345678", mock_mode=True))

    def test_estimate_invent_cost(self):
        cost = estimate_job_cost("invent", {"rows": 200})
        self.assertIsInstance(cost, int)
        self.assertGreater(cost, 0)
        self.assertEqual(cost, 700)  # 200 * 3.5

    def test_estimate_forge_cost(self):
        cost = estimate_job_cost("forge", {"documents": [{"brand": "IFB"}, {"brand": "Voltas"}]})
        self.assertIsInstance(cost, int)
        self.assertGreater(cost, 0)

    def test_estimate_autoscientist_pilot(self):
        cost = estimate_job_cost("autoscientist_pilot", {"row_count": 75})
        self.assertIsInstance(cost, int)
        self.assertEqual(cost, 180)

    def test_estimate_autoscientist_full(self):
        cost = estimate_job_cost("autoscientist_full", {"row_count": 500})
        self.assertIsInstance(cost, int)
        self.assertEqual(cost, 6000)

    def test_credit_budget_exceeded(self):
        set_config(AdaptionConfig(api_key="pt_test_12345678", credit_budget=100, mock_mode=True))
        with self.assertRaises(AdaptionBudgetExceededError):
            estimate_job_cost("invent", {"rows": 500})


class TestDataLifecycle(unittest.TestCase):
    """Tests Requirement 2: Ingestion & Forge, Invent, and Strict Local Deduplication."""

    def setUp(self):
        set_config(AdaptionConfig(api_key="pt_test_12345678", mock_mode=True))

    def test_ingest_and_forge_manuals(self):
        records = ingest_and_forge_manuals()
        self.assertGreater(len(records), 0)
        first = records[0]
        self.assertIsInstance(first, ApplianceRecord)
        self.assertIn(first.brand, ["IFB", "Voltas", "Godrej", "Kent", "Havells", "Blue Star"])
        self.assertIn("Safety", first.response)
        training_dict = first.to_training_dict()
        self.assertIn("instruction", training_dict)
        self.assertIn("response", training_dict)

    def test_invent_synthetic_data(self):
        records = invent_synthetic_data(target_rows=30)
        self.assertEqual(len(records), 30)
        brands = {r.brand for r in records}
        self.assertTrue(any(b in brands for b in ["Voltas", "Godrej", "IFB", "Kent", "Havells"]))
        has_consumer_phrasing = any(
            any(k in r.instruction.lower() for k in ["paani", "cooling", "awaaz", "trip", "machine"])
            for r in records
        )
        self.assertTrue(has_consumer_phrasing)

    def test_strict_local_deduplication(self):
        records = invent_synthetic_data(target_rows=20)
        # Create intentional exact duplicate
        dup_exact = dataclasses.replace(records[0], id="exact_dup_id")
        # Create intentional near duplicate (minor cosmetic suffix)
        dup_near = dataclasses.replace(
            records[1],
            id="near_dup_id",
            consumer_phrasing=records[1].consumer_phrasing + " Please help urgently!!",
            instruction=records[1].instruction + " Please help urgently!!",
        )

        polluted = records + [dup_exact, dup_near]
        self.assertEqual(len(polluted), 22)

        deduped, report = deduplicate_records(polluted, similarity_threshold=0.85)
        self.assertLess(len(deduped), len(polluted))
        self.assertGreaterEqual(report.exact_duplicates_removed, 1)
        self.assertGreaterEqual(report.near_duplicates_removed, 1)
        self.assertEqual(report.final_count, len(deduped))
        self.assertLessEqual(report.retention_rate, 1.0)


class TestAutoScientistWorkflow(unittest.TestCase):
    """Tests Requirement 2C: Pilot micro-exploration (50-100 rows) and Full Scaling."""

    def setUp(self):
        set_config(AdaptionConfig(api_key="pt_test_12345678", mock_mode=True))
        self.dataset = invent_synthetic_data(target_rows=80)

    def test_pilot_size_enforcement(self):
        # Even if 200 requested, safe pilot enforces max 100 rows
        pilot_res = run_autoscientist_pilot(self.dataset, pilot_size=150)
        self.assertLessEqual(pilot_res.row_count, 100)
        self.assertTrue(pilot_res.passed_gate)
        self.assertGreater(pilot_res.convergence_score, 0.8)

    def test_pilot_failure_gate(self):
        # Setting impossibly strict convergence threshold forces quality gate trip
        pilot_res = run_autoscientist_pilot(
            self.dataset, pilot_size=60, min_convergence_score=0.999
        )
        self.assertFalse(pilot_res.passed_gate)
        self.assertIn("Failed", pilot_res.reason)

    def test_full_scaling(self):
        res = run_autoscientist_full_training(self.dataset)
        self.assertIn("checkpoint", res)
        self.assertEqual(res["status"], "succeeded")

    def test_end_to_end_pipeline(self):
        summary = run_appliance_pipeline(
            synthetic_target_rows=60,
            pilot_size=55,
            dedup_threshold=0.85,
        )
        self.assertIn("forged_count", summary)
        self.assertIn("invented_count", summary)
        self.assertIn("pilot_outcome", summary)
        self.assertTrue(summary["pilot_outcome"]["passed_gate"])
        self.assertIn("full_run_result", summary)


if __name__ == "__main__":
    unittest.main()

