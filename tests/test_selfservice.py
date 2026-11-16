from copy import deepcopy
import json
import unittest

from selfservice_assistant import ROOT, answer, demo_guidance, evaluate


class SelfServiceTests(unittest.TestCase):
    def setUp(self):
        self.guidance = demo_guidance()

    def test_connection_guidance_cites_existing_article(self):
        result = answer("Wifi connection is unavailable", self.guidance)
        self.assertEqual(result["decision"], "guidance")
        self.assertEqual(result["sources"][0]["id"], "KB-001")
        self.assertEqual(result["message"], self.guidance[0]["body"])

    def test_application_guidance_preserves_source_text(self):
        result = answer("The application crashes", self.guidance)
        self.assertEqual(result["sources"][0]["id"], "KB-002")
        self.assertIn("reproducible steps", result["message"])

    def test_account_help_does_not_change_access(self):
        result = answer("Change my account permission", self.guidance)
        self.assertEqual(result["sources"][0]["id"], "KB-003")
        self.assertEqual(result["actions_executed"], [])
        self.assertIn("approved identity-verification", result["message"])

    def test_empty_question_requests_clarification(self):
        result = answer(" \n ", self.guidance)
        self.assertEqual(result["decision"], "clarification")
        self.assertEqual(result["sources"], [])

    def test_multiple_topics_request_clarification(self):
        result = answer("Network and account issues", self.guidance)
        self.assertEqual(result["decision"], "clarification")
        self.assertEqual(result["sources"], [])

    def test_unknown_question_prepares_human_handover(self):
        result = answer("Printer paper is jammed", self.guidance)
        self.assertEqual(result["decision"], "escalation")
        self.assertEqual(result["handover"]["symptom"], "Printer paper is jammed")
        self.assertIn("No automated remediation", result["handover"]["checks_completed"])

    def test_credential_values_are_not_echoed(self):
        question = "My token=FAKE-SENSITIVE-VALUE caused an error"
        result = answer(question, self.guidance)
        self.assertEqual(result["decision"], "redaction_required")
        self.assertNotIn("FAKE-SENSITIVE-VALUE", json.dumps(result))
        self.assertIsNone(result["handover"])

    def test_draft_guides_are_not_returned(self):
        self.guidance[0]["status"] = "draft"
        result = answer("Network failure", self.guidance)
        self.assertEqual(result["decision"], "escalation")

    def test_expired_guides_are_not_returned(self):
        self.guidance[0]["review_due"] = "2026-11-15"
        result = answer("Network failure", self.guidance)
        self.assertEqual(result["decision"], "escalation")

    def test_review_date_equal_to_today_remains_current(self):
        self.guidance[0]["review_due"] = "2026-11-16"
        self.assertEqual(answer("Network issue", self.guidance)["decision"], "guidance")

    def test_input_validation_rejects_wrong_type_and_excess_length(self):
        for question in (None, 123, "x" * 501):
            with self.subTest(question_type=type(question).__name__), self.assertRaises(ValueError):
                answer(question, self.guidance)

    def test_result_is_deterministic_without_mutating_guidance(self):
        original = deepcopy(self.guidance)
        first = answer("NETWORK!", self.guidance)
        self.assertEqual(first, answer("NETWORK!", self.guidance))
        self.assertEqual(self.guidance, original)
        self.assertEqual(first["cloud_calls"], 0)

    def test_labelled_queries_match_expected_decisions_and_sources(self):
        cases = json.loads((ROOT / "examples/selfservice-queries.json").read_text())
        result = evaluate(self.guidance, cases)
        self.assertEqual(result["cases"], 12)
        self.assertEqual(result["matched"], 12)
        self.assertEqual(result["fixture_match_rate"], 1.0)

    def test_empty_evaluation_does_not_invent_a_score(self):
        result = evaluate(self.guidance, [])
        self.assertIsNone(result["fixture_match_rate"])
        self.assertEqual(result["cases"], 0)
