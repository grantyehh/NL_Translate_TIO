#!/usr/bin/env python3
"""
Evaluate generated API-friendly TIO JSON-LD outputs.

This is the JSON-LD phase-1 evaluator for the three experiment lines. It checks:
1) JSON syntax
2) Intent payload contract
3) Test spec coverage using expected_tio_elements mapped to JSON-LD fields

The report keeps a few legacy keys (`parse_ok`, `triple_count`,
`expected_coverage_ratio`, `intent_uri_contains_case_id`) so existing comparison
scripts can still aggregate results.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MATCH_CONDITIONS = {
    "LESS_THAN",
    "LESS_THAN_OR_EQUAL",
    "GREATER_THAN",
    "GREATER_THAN_OR_EQUAL",
    "EQUALS",
    "NOT_EQUALS",
}

ROOT = Path(__file__).resolve().parent
EXPERIMENTS = {
    "llm_only": {
        "label": "LLM-only",
        "output_subdir": "llm_only",
        "report_name": "phase1_llm_only.json",
    },
    "graphrag": {
        "label": "GraphRag",
        "output_subdir": "graphrag",
        "report_name": "phase1_graphrag.json",
    },
    "kge_hybrid": {
        "label": "KGE-hybrid",
        "output_subdir": "kge_hybrid",
        "report_name": "phase1_kge_hybrid.json",
    },
}


def test_cases_path() -> Path:
    return ROOT / "test_cases_20.json"


def jsonld_outputs_dir() -> Path:
    return ROOT / "jsonld_outputs"


def phase1_dir() -> Path:
    return ROOT / "phase1"


def strip_markdown_json_fence(raw: str) -> tuple[str, bool]:
    text = raw.strip()
    if not text.startswith("```"):
        return raw, False
    lines = text.splitlines()
    if not lines:
        return raw, False
    lines = lines[1:]
    while lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines) + ("\n" if lines else ""), True


def is_object(value: Any) -> bool:
    return isinstance(value, dict)


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def contract_error(code: str, message: str, path: str) -> dict[str, str]:
    return {"code": code, "message": message, "path": path}


def validate_contract(doc: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not is_object(doc):
        return [contract_error("JSONLD_TOP_LEVEL_OBJECT", "Top-level JSON-LD must be an object.", "$")]

    for key in ("@context", "@type", "id", "name", "description"):
        if not non_empty_string(doc.get(key)):
            errors.append(contract_error("JSONLD_REQUIRED_STRING", f"{key} must be a non-empty string.", f"$.{key}"))
    if doc.get("@type") != "Intent":
        errors.append(contract_error("JSONLD_INTENT_TYPE", '@type must be "Intent".', "$.@type"))

    owner = doc.get("intentOwner")
    if not is_object(owner):
        errors.append(contract_error("JSONLD_INTENT_OWNER", "intentOwner must be an object.", "$.intentOwner"))
    else:
        for key in ("id", "name"):
            if not non_empty_string(owner.get(key)):
                errors.append(
                    contract_error("JSONLD_REQUIRED_STRING", f"intentOwner.{key} must be a non-empty string.", f"$.intentOwner.{key}")
                )

    expectations = doc.get("intentExpectation")
    if not isinstance(expectations, list) or not expectations:
        errors.append(
            contract_error("JSONLD_EXPECTATIONS", "intentExpectation must be a non-empty array.", "$.intentExpectation")
        )
        expectations = []

    for i, expectation in enumerate(expectations):
        exp_path = f"$.intentExpectation[{i}]"
        if not is_object(expectation):
            errors.append(contract_error("JSONLD_EXPECTATION_OBJECT", "Expectation must be an object.", exp_path))
            continue
        for key in ("id", "name", "description", "@type"):
            if not non_empty_string(expectation.get(key)):
                errors.append(contract_error("JSONLD_REQUIRED_STRING", f"{key} must be a non-empty string.", f"{exp_path}.{key}"))
        if expectation.get("@type") not in {"DeliveryExpectation", "PropertyExpectation"}:
            errors.append(
                contract_error(
                    "JSONLD_EXPECTATION_TYPE",
                    "@type must be DeliveryExpectation or PropertyExpectation.",
                    f"{exp_path}.@type",
                )
            )

        obj = expectation.get("expectationObject")
        if not is_object(obj):
            errors.append(
                contract_error("JSONLD_EXPECTATION_OBJECT_REF", "expectationObject must be an object.", f"{exp_path}.expectationObject")
            )
        else:
            for key in ("id", "name", "@type"):
                if not non_empty_string(obj.get(key)):
                    errors.append(
                        contract_error(
                            "JSONLD_REQUIRED_STRING",
                            f"expectationObject.{key} must be a non-empty string.",
                            f"{exp_path}.expectationObject.{key}",
                        )
                    )

        targets = expectation.get("expectationTarget")
        if not isinstance(targets, list) or not targets:
            errors.append(
                contract_error("JSONLD_EXPECTATION_TARGET", "expectationTarget must be a non-empty array.", f"{exp_path}.expectationTarget")
            )
            targets = []

        if expectation.get("@type") == "PropertyExpectation":
            for j, target in enumerate(targets):
                target_path = f"{exp_path}.expectationTarget[{j}]"
                if not is_object(target):
                    errors.append(contract_error("JSONLD_TARGET_OBJECT", "expectationTarget item must be an object.", target_path))
                    continue
                for key in ("name", "targetProperty", "matchCondition"):
                    if not non_empty_string(target.get(key)):
                        errors.append(
                            contract_error("JSONLD_REQUIRED_STRING", f"{key} must be a non-empty string.", f"{target_path}.{key}")
                        )
                if target.get("matchCondition") and target.get("matchCondition") not in MATCH_CONDITIONS:
                    errors.append(
                        contract_error("JSONLD_MATCH_CONDITION", "matchCondition is not a supported enum value.", f"{target_path}.matchCondition")
                    )
                if not is_object(target.get("targetValue")):
                    errors.append(contract_error("JSONLD_TARGET_VALUE", "targetValue must be an object.", f"{target_path}.targetValue"))

    if not isinstance(doc.get("intentContext"), list):
        errors.append(contract_error("JSONLD_CONTEXT_ARRAY", "intentContext must be an array.", "$.intentContext"))
    if not is_object(doc.get("intentReport")):
        errors.append(contract_error("JSONLD_INTENT_REPORT", "intentReport must be an object.", "$.intentReport"))

    return errors


def iter_expectations(doc: dict[str, Any]) -> list[dict[str, Any]]:
    expectations = doc.get("intentExpectation")
    return [x for x in expectations if is_object(x)] if isinstance(expectations, list) else []


def iter_targets(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for expectation in iter_expectations(doc):
        targets = expectation.get("expectationTarget")
        if isinstance(targets, list):
            out.extend(x for x in targets if is_object(x))
    return out


def has_property_target(doc: dict[str, Any]) -> bool:
    return any(
        non_empty_string(target.get("targetProperty")) and is_object(target.get("targetValue"))
        for target in iter_targets(doc)
    )


def expected_element_ok(doc: dict[str, Any], curie: str) -> tuple[bool, str]:
    expectations = iter_expectations(doc)
    contexts = doc.get("intentContext") if isinstance(doc.get("intentContext"), list) else []

    mapping = {
        "icm:Intent": (doc.get("@type") == "Intent", "top-level @type is Intent"),
        "icm:Expectation": (bool(expectations), "intentExpectation has at least one item"),
        "icm:DeliveryExpectation": (
            any(exp.get("@type") == "DeliveryExpectation" for exp in expectations),
            "DeliveryExpectation present in intentExpectation",
        ),
        "icm:PropertyExpectation": (
            any(exp.get("@type") == "PropertyExpectation" for exp in expectations),
            "PropertyExpectation present in intentExpectation",
        ),
        "icm:Target": (bool(iter_targets(doc)), "expectationTarget has at least one target"),
        "icm:Context": (bool(contexts), "intentContext has at least one context item"),
        "log:Condition": (
            any("condition" in str(ctx.get("@type", "")).lower() or "trigger" in str(ctx.get("@type", "")).lower() for ctx in contexts),
            "intentContext includes a condition/trigger context",
        ),
        "icm:valuesOfTargetProperty": (
            has_property_target(doc),
            "PropertyExpectation target has targetProperty and targetValue",
        ),
    }

    if curie in mapping:
        return mapping[curie]
    return False, "No JSON-LD coverage mapping defined for this expected element"


def evaluate_expected_elements(doc: dict[str, Any], expected_elements: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for curie in expected_elements:
        ok, reason = expected_element_ok(doc, curie)
        results.append({"curie": curie, "ok": ok, "reason": reason})
    return results


def count_json_nodes(value: Any) -> int:
    if isinstance(value, dict):
        return 1 + sum(count_json_nodes(v) for v in value.values())
    if isinstance(value, list):
        return 1 + sum(count_json_nodes(v) for v in value)
    return 1


def case_id_slug(case_id: str) -> str:
    return case_id.strip().lower()


def evaluate_payload(
    doc: Any,
    expected_elements: list[str],
    case_id: str,
    file_path: Path,
    markdown_fence_stripped: bool,
    parse_error: str | None,
) -> dict[str, Any]:
    contract_errors = [] if parse_error else validate_contract(doc)
    parse_ok = parse_error is None and not contract_errors and is_object(doc)
    expected_results = evaluate_expected_elements(doc, expected_elements) if is_object(doc) and parse_error is None else []
    coverage = (
        sum(1 for item in expected_results if item.get("ok")) / len(expected_results)
        if expected_results
        else None
    )
    intent_id = str(doc.get("id", "")) if is_object(doc) else ""

    return {
        "file": str(file_path),
        "case_id": case_id,
        "format": "jsonld",
        "parse_ok": parse_ok,
        "parse_error": parse_error,
        "markdown_fence_stripped": markdown_fence_stripped,
        "contract_errors": contract_errors,
        "triple_count": count_json_nodes(doc) if is_object(doc) and parse_error is None else 0,
        "json_node_count": count_json_nodes(doc) if is_object(doc) and parse_error is None else 0,
        "unknown_predicates": [],
        "unknown_types": [],
        "expected_tio_elements": expected_results,
        "expected_coverage_ratio": coverage,
        "intent_uri_contains_case_id": case_id_slug(case_id) in intent_id.lower(),
    }


def evaluate_file(path: Path, expected_elements: list[str], case_id: str) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    cleaned, fenced = strip_markdown_json_fence(raw)
    parse_error: str | None = None
    doc: Any = None
    try:
        doc = json.loads(cleaned)
    except Exception as e:
        parse_error = str(e)
    return evaluate_payload(doc, expected_elements, case_id, path, fenced, parse_error)


def missing_file_report(path: Path, case_id: str) -> dict[str, Any]:
    return {
        "file": str(path),
        "case_id": case_id,
        "format": "jsonld",
        "parse_ok": False,
        "parse_error": "missing output file",
        "markdown_fence_stripped": False,
        "contract_errors": [],
        "triple_count": 0,
        "json_node_count": 0,
        "unknown_predicates": [],
        "unknown_types": [],
        "expected_tio_elements": [],
        "expected_coverage_ratio": None,
        "intent_uri_contains_case_id": False,
    }


def evaluate_experiment(experiment_key: str, test_cases: list[dict[str, Any]]) -> Path | None:
    config = EXPERIMENTS[experiment_key]
    outputs_dir = jsonld_outputs_dir() / config["output_subdir"]
    report_path = phase1_dir() / config["report_name"]
    if not outputs_dir.is_dir():
        print(f"Outputs directory not found: {outputs_dir}", file=sys.stderr)
        return None

    id_to_case = {tc["id"]: tc for tc in test_cases}
    reports: list[dict[str, Any]] = []

    for tc_id in sorted(id_to_case.keys()):
        path = outputs_dir / f"{tc_id}.jsonld"
        if not path.is_file():
            reports.append(missing_file_report(path, tc_id))
            continue
        tc = id_to_case[tc_id]
        reports.append(evaluate_file(path, tc.get("expected_tio_elements", []), tc_id))

    print(f"\n## {config['label']}")
    for row in reports:
        print(f"=== {row['case_id']} ===")
        print(f"  parse_ok: {row['parse_ok']}")
        if row.get("parse_error"):
            print(f"  parse_error: {row['parse_error']}")
        if row.get("contract_errors"):
            print(f"  contract_errors: {len(row['contract_errors'])}")
        if row.get("parse_ok"):
            print(f"  json_node_count: {row['json_node_count']}")
            cov = row.get("expected_coverage_ratio")
            if cov is not None:
                print(f"  expected_tio_elements_met: {cov * 100:.0f}%")
        print()

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(reports, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote JSON report to {report_path}")
    return report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shared phase-1 evaluator for generated TIO JSON-LD.")
    parser.add_argument(
        "experiment",
        nargs="?",
        choices=tuple(EXPERIMENTS.keys()) + ("all",),
        default="all",
        help="Experiment to evaluate: llm_only, graphrag, kge_hybrid, or all (default: all)",
    )
    args = parser.parse_args(argv)

    cases_path = test_cases_path()
    if not cases_path.is_file():
        print(f"Test cases file not found: {cases_path}", file=sys.stderr)
        return 2

    test_cases = json.loads(cases_path.read_text(encoding="utf-8"))
    experiment_keys = list(EXPERIMENTS.keys()) if args.experiment == "all" else [args.experiment]
    ok = True
    for experiment_key in experiment_keys:
        ok = evaluate_experiment(experiment_key, test_cases) is not None and ok

    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
