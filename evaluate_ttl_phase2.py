#!/usr/bin/env python3
"""
Phase-2 evaluator for generated Turtle.

Adds golden-answer checks on top of the existing phase-1 signals:
- syntax / parse_ok
- vocabulary legality
- expected_tio_elements coverage
- must_have_triples structural checks
- must_not_have_predicates checks

This version includes a pragmatic first-pass `expected_values` checker:
- scans literals and raw Turtle text
- checks expected numeric values, units, operator hints, and keywords
- does not yet perform full semantic graph reasoning
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

FUN = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/")

TIO_PREFIXES = {
    "icm": "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/",
    "imo": "http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/",
    "fun": "http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/",
    "log": "http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/",
    "math": "http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions/",
    "set": "http://tio.models.tmforum.org/tio/v3.6.0/SetOperators/",
}

EXTRA_PREFIXES = {
    "rdf": str(RDF),
    "rdfs": str(RDFS),
    "xsd": str(XSD),
}

ALL_PREFIXES = {**TIO_PREFIXES, **EXTRA_PREFIXES}

STANDARD_PREDICATE_PREFIXES = (
    str(RDF),
    str(RDFS),
    str(XSD),
    "http://purl.org/dc/terms/",
    "http://www.w3.org/2004/02/skos/core#",
    "http://www.w3.org/2006/time#",
)

ONTOLOGY_PREFIX_PREAMBLE = """
@prefix icm:  <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix imo:  <http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/> .
@prefix fun:  <http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/> .
@prefix log:  <http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/> .
@prefix math: <http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions/> .
@prefix mf:   <http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions> .
@prefix set:  <http://tio.models.tmforum.org/tio/v3.6.0/SetOperators/> .
@prefix met:  <http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/> .
@prefix quan: <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .
@prefix ig:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentGuaranteeOntology/> .
@prefix insp: <http://tio.models.tmforum.org/tio/v3.6.0/IntentSpecification/> .
@prefix pbi:  <http://tio.models.tmforum.org/tio/v3.6.0/ProposalBestIntent/> .
@prefix pro:  <http://tio.models.tmforum.org/tio/v3.6.0/IntentProbing/> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix t:    <http://www.w3.org/2006/time#> .
"""


def strip_markdown_turtle_fence(raw: str) -> tuple[str, bool]:
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


def parse_prefix_map(turtle_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in re.finditer(
        r"^@prefix\s+([A-Za-z_][\w-]*)\s*:\s*<([^>]+)>\s*\.\s*$",
        turtle_text,
        flags=re.MULTILINE,
    ):
        out[m.group(1)] = m.group(2)
    return out


def load_reference_vocabulary(ontology_dir: Path) -> tuple[set[URIRef], set[URIRef]]:
    ref = Graph()
    for p in sorted(ontology_dir.glob("*.ttl")):
        g = Graph()
        body = p.read_text(encoding="utf-8")
        g.parse(data=ONTOLOGY_PREFIX_PREAMBLE + body, format="turtle")
        ref += g
    classes: set[URIRef] = set()
    props: set[URIRef] = set()
    for s, _, _ in ref.triples((None, RDF.type, RDFS.Class)):
        if isinstance(s, URIRef):
            classes.add(s)
    for s, _, _ in ref.triples((None, RDF.type, RDF.Property)):
        if isinstance(s, URIRef):
            props.add(s)
    for s, _, _ in ref.triples((None, RDF.type, FUN.Function)):
        if isinstance(s, URIRef):
            props.add(s)
    return classes, props


def expand_curie(curie: str) -> URIRef:
    if ":" not in curie:
        raise ValueError(f"Not a CURIE: {curie!r}")
    prefix, name = curie.split(":", 1)
    if prefix not in ALL_PREFIXES:
        raise ValueError(f"Unknown prefix in CURIE {curie!r} (supported: {sorted(ALL_PREFIXES)})")
    return URIRef(ALL_PREFIXES[prefix] + name)


def predicate_is_external(p: URIRef) -> bool:
    s = str(p)
    return any(s.startswith(pref) for pref in STANDARD_PREDICATE_PREFIXES)


def case_id_slug(case_id: str) -> str:
    return case_id.strip().lower()


def coerce_ratio(expected_results: list[dict[str, Any]]) -> float | None:
    if not expected_results:
        return None
    return sum(1 for e in expected_results if e.get("ok")) / len(expected_results)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def collect_text_corpus(g: Graph, cleaned: str) -> str:
    parts = [normalize_text(cleaned)]
    for s, p, o in g:
        parts.append(normalize_text(str(s)))
        parts.append(normalize_text(str(p)))
        parts.append(normalize_text(str(o)))
    return " ".join(part for part in parts if part)


def value_patterns(value: Any) -> list[str]:
    if isinstance(value, (int, float)):
        text = format(value, "g")
        patterns = [re.escape(text)]
        if "." in text:
            patterns.append(re.escape(f"{float(value):.2f}".rstrip("0").rstrip(".")))
        return patterns
    text = str(value).strip()
    if "-" in text and ":" in text:
        start, end = text.split("-", 1)
        patterns = [
            re.escape(text.lower()),
            rf"{re.escape(start.lower())}\s*(?:-|to)\s*{re.escape(end.lower())}",
        ]
        return patterns
    return [re.escape(text.lower())]


def unit_patterns(unit: str) -> list[str]:
    unit = normalize_text(unit)
    mapping = {
        "%": [r"%", r"\bpercent\b"],
        "mbps": [r"\bmbps\b", r"\bmb/s\b"],
        "ms": [r"\bms\b", r"\bmillisecond", r"\bmsec\b"],
        "seconds": [r"\bseconds?\b", r"\bsecs?\b", r"\b30\b"],
        "x": [r"\bx\b", r"\btimes\b", r"\bdouble", r"\bdoubled\b", r"\btwofold\b"],
    }
    return mapping.get(unit, [re.escape(unit)])


def operator_patterns(op: str, value: Any) -> list[str]:
    op = str(op).strip().lower()
    value_text = format(value, "g").lower() if isinstance(value, (int, float)) else str(value).strip().lower()
    mapping = {
        "<": [r"\bbelow\b", r"\blower than\b", r"\bless than\b", rf"<\s*{re.escape(value_text)}"],
        "<=": [r"\bat most\b", r"\bno more than\b", r"\bwithin\b", rf"<=\s*{re.escape(value_text)}"],
        ">": [r"\babove\b", r"\bhigher than\b", r"\bgreater than\b", rf">\s*{re.escape(value_text)}"],
        ">=": [r"\bat least\b", r"\bnot less than\b", r"\bno lower than\b", rf">=\s*{re.escape(value_text)}"],
        "=": [r"\bequal\b", r"\bset to\b", r"\bhighest\b"],
        "during": [r"\bduring\b", r"\bbetween\b", r"\bfrom\b"],
        "if": [r"\bif\b", r"\bwhen\b"],
        "limit": [r"\blimit\b", r"\breduce\b", r"\bthrottle\b"],
        "maintain": [r"\bmaintain\b", r"\buninterrupted\b", r"\bwithout interruption\b"],
    }
    return mapping.get(op, [re.escape(op)])


def evaluate_expected_values(g: Graph, cleaned: str, expected_values: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], float | None]:
    if not expected_values:
        return [], None

    corpus = collect_text_corpus(g, cleaned)
    results: list[dict[str, Any]] = []
    for item in expected_values:
        value = item.get("value")
        unit = item.get("unit")
        operator = item.get("operator")
        keywords = [normalize_text(str(k)) for k in item.get("keywords", [])]

        value_ok = any(re.search(pattern, corpus) for pattern in value_patterns(value)) if value is not None else True
        unit_ok = any(re.search(pattern, corpus) for pattern in unit_patterns(str(unit))) if unit else True
        operator_ok = any(re.search(pattern, corpus) for pattern in operator_patterns(operator, value)) if operator else True
        keywords_ok = any(keyword in corpus for keyword in keywords) if keywords else True

        checks = {
            "value_ok": value_ok,
            "unit_ok": unit_ok,
            "operator_ok": operator_ok,
            "keywords_ok": keywords_ok,
        }
        applicable = 4 if keywords else 3
        matched = sum(1 for passed in checks.values() if passed)
        score = matched / applicable
        ok = value_ok and score >= 0.5
        failed = [name for name, passed in checks.items() if not passed]
        reason = "matched expected value hints" if ok else f"missing: {', '.join(failed)}"

        results.append(
            {
                **item,
                **checks,
                "score": score,
                "ok": ok,
                "reason": reason,
            }
        )

    score = sum(1 for item in results if item["ok"]) / len(results)
    return results, score


def is_var(term: str) -> bool:
    return isinstance(term, str) and term.startswith("?")


def term_matches(pattern_term: str, actual: Any, bindings: dict[str, Any]) -> dict[str, Any] | None:
    new_bindings = dict(bindings)
    if is_var(pattern_term):
        if pattern_term in new_bindings:
            return new_bindings if new_bindings[pattern_term] == actual else None
        new_bindings[pattern_term] = actual
        return new_bindings
    expected = expand_curie(pattern_term)
    return new_bindings if actual == expected else None


def match_patterns(graph: Graph, patterns: list[dict[str, str]], bindings: dict[str, Any] | None = None) -> tuple[bool, dict[str, Any] | None]:
    bindings = {} if bindings is None else bindings
    if not patterns:
        return True, bindings

    current = patterns[0]
    rest = patterns[1:]
    for s, p, o in graph:
        b1 = term_matches(current["subject"], s, bindings)
        if b1 is None:
            continue
        b2 = term_matches(current["predicate"], p, b1)
        if b2 is None:
            continue
        b3 = term_matches(current["object"], o, b2)
        if b3 is None:
            continue
        ok, final_bindings = match_patterns(graph, rest, b3)
        if ok:
            return True, final_bindings
    return False, None


def evaluate_expected_elements(
    g: Graph,
    expected_elements: list[str],
    ref_classes: set[URIRef],
    ref_properties: set[URIRef],
) -> list[dict[str, Any]]:
    expected_results: list[dict[str, Any]] = []
    for curie in expected_elements:
        item: dict[str, Any] = {"curie": curie, "ok": False, "reason": ""}
        try:
            iri = expand_curie(curie)
        except ValueError as e:
            item["reason"] = str(e)
            expected_results.append(item)
            continue
        item["iri"] = str(iri)
        if iri in ref_classes:
            met = any(g.triples((None, RDF.type, iri)))
            item["ok"] = met
            item["reason"] = "instance of class" if met else "no rdf:type with this class IRI"
        elif iri in ref_properties:
            met = any(g.triples((None, iri, None)))
            item["ok"] = met
            item["reason"] = "property used on at least one triple" if met else "property never used as predicate"
        else:
            item["reason"] = "IRI not found as rdfs:Class or rdf:Property in reference ontology files"
        expected_results.append(item)
    return expected_results


def evaluate_golden_case(g: Graph, cleaned: str, golden_case: dict[str, Any] | None) -> dict[str, Any] | None:
    if golden_case is None:
        return None

    triple_patterns = golden_case.get("must_have_triples", [])
    triple_match_ok, bindings = match_patterns(g, triple_patterns) if triple_patterns else (True, {})

    must_not_results: list[dict[str, Any]] = []
    for curie in golden_case.get("must_not_have_predicates", []):
        iri = expand_curie(curie)
        present = any(g.triples((None, iri, None)))
        must_not_results.append(
            {
                "curie": curie,
                "iri": str(iri),
                "ok": not present,
                "reason": "predicate absent" if not present else "predicate appears in generated graph",
            }
        )

    must_not_ok = all(item["ok"] for item in must_not_results) if must_not_results else True

    expected_values_results, expected_values_score = evaluate_expected_values(
        g,
        cleaned,
        golden_case.get("expected_values", []),
    )

    checks = []
    if triple_patterns:
        checks.append(1.0 if triple_match_ok else 0.0)
    if must_not_results:
        checks.append(sum(1 for item in must_not_results if item["ok"]) / len(must_not_results))
    if expected_values_results:
        checks.append(expected_values_score if expected_values_score is not None else 0.0)
    structural_score = sum(checks) / len(checks) if checks else None

    return {
        "golden_ttl_file": golden_case.get("golden_ttl_file"),
        "must_have_triples_ok": triple_match_ok,
        "must_have_triples_count": len(triple_patterns),
        "must_have_triples_bindings": {k: str(v) for k, v in (bindings or {}).items()},
        "must_not_have_predicates_ok": must_not_ok,
        "must_not_have_predicates_results": must_not_results,
        "expected_values_results": expected_values_results,
        "expected_values_ok": all(item["ok"] for item in expected_values_results) if expected_values_results else True,
        "expected_values_score": expected_values_score,
        "structural_score": structural_score,
        "notes": golden_case.get("notes"),
    }


def evaluate_file(
    path: Path,
    ref_classes: set[URIRef],
    ref_properties: set[URIRef],
    expected_elements: list[str],
    case_id: str,
    golden_case: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    cleaned, fenced = strip_markdown_turtle_fence(raw)
    g = Graph()
    parse_error: str | None = None
    try:
        g.parse(data=cleaned, format="turtle")
    except Exception as e:
        parse_error = str(e)

    prefix_map = parse_prefix_map(cleaned)
    slug = case_id_slug(case_id)

    prefix_checks: dict[str, dict[str, str | bool]] = {}
    for pref, expected in TIO_PREFIXES.items():
        if pref in prefix_map:
            prefix_checks[pref] = {
                "declared": prefix_map[pref],
                "expected": expected,
                "matches_official": prefix_map[pref] == expected,
            }

    unknown_predicates: list[str] = []
    unknown_types: list[str] = []
    expected_results: list[dict[str, Any]] = []
    golden_results: dict[str, Any] | None = None
    intent_uri_hint_ok = False

    if parse_error is None:
        for p in set(g.predicates()):
            if not isinstance(p, URIRef):
                continue
            if predicate_is_external(p):
                continue
            if p not in ref_properties:
                unknown_predicates.append(str(p))

        for o in g.objects(None, RDF.type):
            if not isinstance(o, URIRef):
                continue
            if str(o).startswith("http://www.w3.org/"):
                continue
            if o not in ref_classes:
                unknown_types.append(str(o))

        expected_results = evaluate_expected_elements(g, expected_elements, ref_classes, ref_properties)
        golden_results = evaluate_golden_case(g, cleaned, golden_case)

        for s in g.subjects(RDF.type, None):
            if isinstance(s, URIRef) and slug in str(s).lower():
                intent_uri_hint_ok = True
                break

    return {
        "file": str(path),
        "case_id": case_id,
        "parse_ok": parse_error is None,
        "parse_error": parse_error,
        "markdown_fence_stripped": fenced,
        "triple_count": len(g) if parse_error is None else 0,
        "prefix_checks": prefix_checks,
        "unknown_predicates": sorted(set(unknown_predicates)),
        "unknown_types": sorted(set(unknown_types)),
        "expected_tio_elements": expected_results,
        "expected_coverage_ratio": coerce_ratio(expected_results),
        "intent_uri_contains_case_id": intent_uri_hint_ok,
        "golden_case_present": golden_case is not None,
        "golden_evaluation": golden_results,
    }


def load_golden_cases(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Golden cases file must be a JSON array: {path}")
    return {str(item["id"]): item for item in data if isinstance(item, dict) and item.get("id")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-2 evaluator with golden-answer structural checks.")
    parser.add_argument(
        "--ontology-dir",
        type=Path,
        default=Path("TM Forum Intent Ontology"),
        help="Directory with official TIO .ttl modules (default: TM Forum Intent Ontology)",
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        required=True,
        help="Generated .ttl directory to evaluate",
    )
    parser.add_argument(
        "--test-cases",
        type=Path,
        default=Path("test_cases_20.json"),
        help="Test cases JSON (default: test_cases_20.json)",
    )
    parser.add_argument(
        "--golden-cases",
        type=Path,
        default=Path("goldens/golden_cases.json"),
        help="Golden cases JSON (default: goldens/golden_cases.json)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="If set, write full report as JSON to this path",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    ontology_dir = (root / args.ontology_dir).resolve() if not args.ontology_dir.is_absolute() else args.ontology_dir
    outputs_dir = (root / args.outputs_dir).resolve() if not args.outputs_dir.is_absolute() else args.outputs_dir
    test_cases_path = (root / args.test_cases).resolve() if not args.test_cases.is_absolute() else args.test_cases
    golden_cases_path = (root / args.golden_cases).resolve() if not args.golden_cases.is_absolute() else args.golden_cases

    if not ontology_dir.is_dir():
        print(f"Ontology directory not found: {ontology_dir}", file=sys.stderr)
        return 2
    if not outputs_dir.is_dir():
        print(f"Outputs directory not found: {outputs_dir}", file=sys.stderr)
        return 2
    if not test_cases_path.is_file():
        print(f"Test cases file not found: {test_cases_path}", file=sys.stderr)
        return 2
    if not golden_cases_path.is_file():
        print(f"Golden cases file not found: {golden_cases_path}", file=sys.stderr)
        return 2

    ref_classes, ref_properties = load_reference_vocabulary(ontology_dir)
    test_cases = json.loads(test_cases_path.read_text(encoding="utf-8"))
    id_to_case = {tc["id"]: tc for tc in test_cases}
    golden_cases = load_golden_cases(golden_cases_path)

    reports: list[dict[str, Any]] = []
    for tc_id in sorted(id_to_case.keys()):
        ttl_path = outputs_dir / f"{tc_id}.ttl"
        golden_case = golden_cases.get(tc_id)
        if not ttl_path.is_file():
            reports.append(
                {
                    "file": str(ttl_path),
                    "case_id": tc_id,
                    "parse_ok": False,
                    "parse_error": "missing output file",
                    "markdown_fence_stripped": False,
                    "triple_count": 0,
                    "prefix_checks": {},
                    "unknown_predicates": [],
                    "unknown_types": [],
                    "expected_tio_elements": [],
                    "expected_coverage_ratio": None,
                    "intent_uri_contains_case_id": False,
                    "golden_case_present": golden_case is not None,
                    "golden_evaluation": None,
                }
            )
            continue
        tc = id_to_case[tc_id]
        reports.append(
            evaluate_file(
                ttl_path,
                ref_classes,
                ref_properties,
                tc.get("expected_tio_elements", []),
                tc_id,
                golden_case,
            )
        )

    print(f"Reference vocabulary: {len(ref_classes)} classes, {len(ref_properties)} properties from {ontology_dir}")
    print(f"Golden cases loaded : {len(golden_cases)} from {golden_cases_path}")
    print()

    for r in reports:
        print(f"=== {r['case_id']} ===")
        print(f"  parse_ok: {r['parse_ok']}")
        if not r["parse_ok"] and r.get("parse_error"):
            print(f"  parse_error: {r['parse_error']}")
        if r.get("parse_ok"):
            cov = r.get("expected_coverage_ratio")
            if cov is not None:
                print(f"  expected_tio_elements_met: {cov * 100:.0f}%")
            ge = r.get("golden_evaluation")
            if ge:
                print(f"  golden.must_have_triples_ok: {ge['must_have_triples_ok']}")
                print(f"  golden.must_not_have_predicates_ok: {ge['must_not_have_predicates_ok']}")
                print(f"  golden.expected_values_ok: {ge['expected_values_ok']}")
                if ge.get("structural_score") is not None:
                    print(f"  golden.structural_score: {ge['structural_score']:.2f}")
        print()

    if args.json_out:
        out_path = (root / args.json_out).resolve() if not args.json_out.is_absolute() else args.json_out
        out_path.write_text(json.dumps(reports, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote JSON report to {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
