import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("process_classifier", ROOT / "tools" / "process_classifier.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def valid_record():
    flags = {key: False for key in MODULE.OPERATION_FLOORS}
    surfaces = {key: False for key in MODULE.SURFACES}
    return {
        "declared_process_level": "P0",
        "affected_paths": [{"path": "a.py", "component": "core", "effect": "modify"}],
        "affected_components": ["core"],
        "operation_flags": flags,
        "protected_surfaces": surfaces,
        "risk_evidence": {
            "failure_frequency": "none", "ambiguity": "low", "blast_radius": "local",
            "known_solution_confidence": "high", "dependency_volatility": "low",
            "rollback_difficulty": "easy", "evidence_refs": ["spec:TCS-005"],
        },
        "lightweight_route": {
            "implementation_intensity": "LOW", "scope_bounded": True,
            "success_conditions_bound": True, "minimum_tests_bound": True, "single_actor": True,
            "unresolved_failure": False, "external_app": False, "persistent_data": False,
            "distribution_change": False, "destructive_operation": False, "protected_surface": False,
        },
    }


class ProcessClassifierTests(unittest.TestCase):
    def test_single_write_raises_to_p1_and_allows_lightweight(self):
        result = MODULE.classify(valid_record())
        self.assertEqual(result["corrected_process_level"], "P1")
        self.assertEqual(result["route"], "lightweight")

    def test_multiple_components_raise_to_p3(self):
        record = valid_record()
        record["affected_components"].append("ui")
        record["affected_paths"].append({"path": "ui.py", "component": "ui", "effect": "create"})
        result = MODULE.classify(record)
        self.assertEqual(result["corrected_process_level"], "P3")
        self.assertEqual(result["route"], "standard")

    def test_operation_and_risk_floors_never_lower_declaration(self):
        record = valid_record()
        record["declared_process_level"] = "P4"
        record["risk_evidence"]["rollback_difficulty"] = "difficult"
        result = MODULE.classify(record)
        self.assertEqual(result["corrected_process_level"], "P4")
        self.assertFalse(result["process_level_changed"])

    def test_protected_surface_sets_floor_approval_tests_and_standard_route(self):
        record = valid_record()
        record["operation_flags"]["external_app"] = True
        record["protected_surfaces"]["external_app"] = True
        record["lightweight_route"]["external_app"] = True
        record["lightweight_route"]["protected_surface"] = True
        result = MODULE.classify(record)
        self.assertEqual(result["corrected_process_level"], "P3")
        self.assertEqual(result["approval"], "approved_contract")
        self.assertIn("limited_real_app_test", result["mandatory_verification"])
        self.assertEqual(result["route"], "standard")

    def test_p4_surface_requires_explicit_human(self):
        record = valid_record()
        record["operation_flags"]["security_boundary"] = True
        record["protected_surfaces"]["security_boundary"] = True
        record["lightweight_route"]["protected_surface"] = True
        result = MODULE.classify(record)
        self.assertEqual(result["corrected_process_level"], "P4")
        self.assertEqual(result["approval"], "explicit_human")

    def test_distribution_risk_is_p4_evidence(self):
        record = valid_record()
        record["risk_evidence"]["blast_radius"] = "distribution"
        result = MODULE.classify(record)
        self.assertEqual(result["corrected_process_level"], "P4")

    def test_path_traversal_and_missing_evidence_need_review(self):
        record = valid_record()
        record["affected_paths"][0]["path"] = "../a.py"
        record["risk_evidence"]["evidence_refs"] = []
        result = MODULE.classify(record)
        self.assertTrue(result["needs_review"])
        self.assertIsNone(result["corrected_process_level"])

    def test_contradictory_route_facts_need_review(self):
        record = valid_record()
        record["operation_flags"]["persistent_data"] = True
        result = MODULE.classify(record)
        self.assertIn("lightweight_fact_conflict", result["review_reasons"])


if __name__ == "__main__":
    unittest.main()
