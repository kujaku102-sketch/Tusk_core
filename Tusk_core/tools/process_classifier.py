"""Mechanical Process Level, Protected Surface, and route classifier."""

import argparse
import json
import sys
from pathlib import PurePosixPath


LEVELS = {f"P{value}": value for value in range(5)}
WRITE_EFFECTS = {"modify", "create", "delete"}
EFFECTS = {"read_only", "metadata_only", *WRITE_EFFECTS}
OPERATION_FLOORS = {
    "external_app": "P3", "persistent_settings": "P2", "persistent_data": "P3",
    "migration": "P3", "release": "P4", "distribution": "P4",
    "installer": "P4", "update_or_uninstall": "P4",
    "destructive_or_irreversible": "P4", "security_boundary": "P4",
    "broad_user_data": "P4",
}
SURFACES = {
    "security_boundary": ("P4", "explicit_human", "security_tests+full_regression+integration+rollback_test"),
    "authentication": ("P4", "explicit_human", "auth_positive_negative+security_tests+full_regression+integration+rollback_test"),
    "secrets": ("P4", "explicit_human", "secret_absence_scan+security_tests+full_regression+integration+rollback_test"),
    "distribution_installer": ("P4", "explicit_human", "full_regression+integration+install_update_uninstall+manifest_hash+rollback_test"),
    "destructive_operation": ("P4", "explicit_human", "isolated_dry_run+full_regression+integration+recovery_test+rollback_test"),
    "user_data": ("P3", "approved_contract", "unit+related_regression+integration+data_integrity+recovery_test"),
    "persistent_schema": ("P3", "approved_contract", "schema_validation+forward_backward_migration+related_regression+integration+rollback_test"),
    "process_stop": ("P3", "approved_contract", "pid_identity+stop_scope+unit+related_regression+integration+recovery_test"),
    "external_app": ("P3", "approved_contract", "dependency_precheck+unit+related_regression+integration+limited_real_app_test+recovery_test"),
}
RISK_VALUES = {
    "failure_frequency": {"none", "isolated", "repeated"},
    "ambiguity": {"low", "medium", "high"},
    "blast_radius": {"local", "component", "cross_component", "distribution"},
    "known_solution_confidence": {"unknown", "low", "medium", "high"},
    "dependency_volatility": {"low", "medium", "high"},
    "rollback_difficulty": {"easy", "bounded", "difficult", "irreversible"},
}
ROUTE_BOOLS = (
    "scope_bounded", "success_conditions_bound", "minimum_tests_bound", "single_actor",
    "unresolved_failure", "external_app", "persistent_data", "distribution_change",
    "destructive_operation", "protected_surface",
)


def _normal_path(value):
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and value == path.as_posix() and ".." not in path.parts and value != "."


def _review(declared, reasons):
    return {
        "declared_process_level": declared if declared in LEVELS else None,
        "corrected_process_level": None,
        "process_level_changed": False,
        "correction_reasons": [],
        "protected_surface": None,
        "surface_ids": [],
        "approval": None,
        "mandatory_verification": [],
        "route": "standard",
        "state": "needs_review",
        "needs_review": True,
        "review_reasons": sorted(set(reasons)),
    }


def classify(record):
    """Validate a classification record and return a deterministic decision."""
    if not isinstance(record, dict):
        return _review(None, ["invalid_record"])
    declared = record.get("declared_process_level")
    reasons = []
    if declared not in LEVELS:
        reasons.append("invalid_declared_process_level")

    paths = record.get("affected_paths")
    components = record.get("affected_components")
    flags = record.get("operation_flags")
    surfaces = record.get("protected_surfaces")
    risk = record.get("risk_evidence")
    route = record.get("lightweight_route")
    if not isinstance(paths, list): reasons.append("invalid_affected_paths"); paths = []
    if not isinstance(components, list) or any(not isinstance(x, str) or not x for x in components):
        reasons.append("invalid_affected_components"); components = []
    elif len(components) != len(set(components)):
        reasons.append("duplicate_affected_component")

    seen_paths = set()
    for item in paths:
        if not isinstance(item, dict) or set(item) != {"path", "component", "effect"}:
            reasons.append("invalid_affected_path_record"); continue
        path, component, effect = item["path"], item["component"], item["effect"]
        if not _normal_path(path): reasons.append("invalid_or_non_normalized_path")
        if path in seen_paths: reasons.append("duplicate_path")
        seen_paths.add(path)
        if component not in components: reasons.append("path_component_not_declared")
        if effect not in EFFECTS: reasons.append("invalid_path_effect")

    if not isinstance(flags, dict) or set(flags) != set(OPERATION_FLOORS) or any(type(v) is not bool for v in flags.values()):
        reasons.append("invalid_operation_flags"); flags = {}
    if not isinstance(surfaces, dict) or set(surfaces) != set(SURFACES) or any(type(v) is not bool for v in surfaces.values()):
        reasons.append("invalid_protected_surfaces"); surfaces = {}
    if not isinstance(risk, dict) or set(risk) != {*RISK_VALUES, "evidence_refs"}:
        reasons.append("invalid_risk_evidence"); risk = {}
    else:
        for key, allowed in RISK_VALUES.items():
            if risk[key] not in allowed: reasons.append(f"invalid_risk_{key}")
        refs = risk["evidence_refs"]
        if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or not x for x in refs):
            reasons.append("missing_risk_evidence_refs")
    if not isinstance(route, dict) or set(route) != set(ROUTE_BOOLS) | {"implementation_intensity"}:
        reasons.append("invalid_lightweight_route_record"); route = {}
    else:
        if any(type(route[key]) is not bool for key in ROUTE_BOOLS): reasons.append("invalid_lightweight_route_boolean")
        if route["implementation_intensity"] not in {"LOW", "MID", "HIGH", "MAX"}: reasons.append("invalid_implementation_intensity")

    assertions = record.get("operation_assertions", {})
    if not isinstance(assertions, dict) or any(k not in OPERATION_FLOORS or type(v) is not bool for k, v in assertions.items()):
        reasons.append("invalid_operation_assertions")
    elif flags and any(assertions[k] != flags[k] for k in assertions):
        reasons.append("contradictory_operation_assertion")
    if surfaces and flags:
        if surfaces["external_app"] != flags["external_app"]:
            reasons.append("external_app_surface_flag_conflict")
        if surfaces["security_boundary"] != flags["security_boundary"]:
            reasons.append("security_boundary_surface_flag_conflict")
        if surfaces["distribution_installer"] and not any(flags[k] for k in ("release", "distribution", "installer", "update_or_uninstall")):
            reasons.append("distribution_surface_flag_conflict")
        if surfaces["destructive_operation"] != flags["destructive_or_irreversible"]:
            reasons.append("destructive_surface_flag_conflict")
    if route and flags and surfaces:
        expected = {
            "external_app": flags["external_app"], "persistent_data": flags["persistent_data"],
            "distribution_change": any(flags[k] for k in ("release", "distribution", "installer", "update_or_uninstall")),
            "destructive_operation": flags["destructive_or_irreversible"],
            "protected_surface": any(surfaces.values()),
        }
        if any(route[k] != v for k, v in expected.items()): reasons.append("lightweight_fact_conflict")
    if reasons:
        return _review(declared, reasons)

    write_paths = [p for p in paths if p["effect"] in WRITE_EFFECTS]
    write_components = {p["component"] for p in write_paths}
    if not write_paths: scope_floor = "P0"
    elif len(write_paths) == 1 and len(write_components) == 1: scope_floor = "P1"
    elif len(write_components) == 1: scope_floor = "P2"
    else: scope_floor = "P3"
    candidates = [("scope", scope_floor, "affected_paths")]
    candidates.extend((key, floor, f"operation_flags.{key}") for key, floor in OPERATION_FLOORS.items() if flags[key])
    active_surfaces = sorted(key for key, value in surfaces.items() if value)
    candidates.extend(("protected_surface", SURFACES[key][0], key) for key in active_surfaces)
    if risk["blast_radius"] == "cross_component": candidates.append(("risk_evidence", "P3", "risk_evidence.blast_radius"))
    if risk["blast_radius"] == "distribution": candidates.append(("risk_evidence", "P4", "risk_evidence.blast_radius"))
    if risk["rollback_difficulty"] == "difficult": candidates.append(("risk_evidence", "P3", "risk_evidence.rollback_difficulty"))
    if risk["rollback_difficulty"] == "irreversible": candidates.append(("risk_evidence", "P4", "risk_evidence.rollback_difficulty"))
    corrected_value = max([LEVELS[declared], *(LEVELS[floor] for _, floor, _ in candidates)])
    corrected = f"P{corrected_value}"
    corrections = [
        {"rule": rule, "from": declared, "required": floor, "evidence": evidence}
        for rule, floor, evidence in candidates if LEVELS[floor] > LEVELS[declared]
    ]
    approval = "none"
    if active_surfaces:
        approval = "explicit_human" if any(SURFACES[key][1] == "explicit_human" for key in active_surfaces) else "approved_contract"
    verification = sorted({item for key in active_surfaces for item in SURFACES[key][2].split("+")})
    lightweight = (
        corrected_value <= 1 and route["implementation_intensity"] in {"LOW", "MID"}
        and all(route[key] for key in ("scope_bounded", "success_conditions_bound", "minimum_tests_bound", "single_actor"))
        and not any(route[key] for key in ("unresolved_failure", "external_app", "persistent_data", "distribution_change", "destructive_operation", "protected_surface"))
    )
    return {
        "declared_process_level": declared, "corrected_process_level": corrected,
        "process_level_changed": corrected != declared, "correction_reasons": corrections,
        "protected_surface": bool(active_surfaces), "surface_ids": active_surfaces,
        "approval": approval, "mandatory_verification": verification,
        "route": "lightweight" if lightweight else "standard", "state": "ready",
        "needs_review": False, "review_reasons": [],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="JSON input file; stdin when omitted")
    args = parser.parse_args(argv)
    try:
        with open(args.input, encoding="utf-8") if args.input else sys.stdin as stream:
            record = json.load(stream)
        result = classify(record)
    except (OSError, json.JSONDecodeError) as error:
        result = _review(None, [f"input_error:{type(error).__name__}"])
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 2 if result["needs_review"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
