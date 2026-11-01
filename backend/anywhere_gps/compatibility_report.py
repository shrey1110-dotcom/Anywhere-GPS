"""Compatibility report built ONLY from observations recorded on physical devices (compat/results.json).

Outcomes are deliberately granular; a Location Probe pass never implies a third-party app accepts the location.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

APPS = ["Apple Maps", "Find My", "Snapchat", "Costco", "Walmart", "Target", "Amazon", "DoorDash", "Uber", "ADP Mobile"]
OUTCOMES = {
    "core_location_simulation_verified",      # Location Probe on a physical device saw the simulated fix
    "gps_permission_behavior_observed",
    "location_ui_behavior_observed",
    "attendance_acceptance_unverified",       # default for ADP
    "approved_test_acceptance_verified",      # ONLY with genuine employer-authorized evidence
    "not_tested",
}
EVIDENCE_REQUIRED = {"approved_test_acceptance_verified"}


def load_results(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text()) if path.exists() else []


def validate_entry(e: dict[str, Any]) -> list[str]:
    errs = []
    if e.get("app") not in APPS:
        errs.append(f"unknown app {e.get('app')!r}")
    if e.get("outcome") not in OUTCOMES:
        errs.append(f"unknown outcome {e.get('outcome')!r}")
    if e.get("outcome") != "not_tested" and not e.get("physical_device"):
        errs.append("physical_device (model + iOS version) is required for any observed result")
    if e.get("outcome") in EVIDENCE_REQUIRED and not e.get("authorization_reference"):
        errs.append("authorization_reference (employer-approved test) is required for this outcome")
    return errs


def build_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for app in APPS:
        entries = [e for e in results if e.get("app") == app and not validate_entry(e)]
        rows.append({"app": app, "outcomes": sorted({e["outcome"] for e in entries}) or ["not_tested"],
                     "observations": len(entries)})
    invalid = [{"entry": e, "errors": validate_entry(e)} for e in results if validate_entry(e)]
    return {"rows": rows, "rejected_entries": invalid,
            "note": "Rows reflect only validated physical-device observations. 'not_tested' means no evidence."}
