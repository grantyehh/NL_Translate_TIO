#!/usr/bin/env python3
"""
Evaluate generated Turtle outputs against:
1) Syntax — RDF 1.1 Turtle parsing
2) Vocabulary — classes/properties found in TM Forum TIO ontology files
3) Test spec — expected_tio_elements from the shared test cases JSON

This is the shared phase-1 evaluator used by every experiment line.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

FUN = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/")

TIO_PREFIXES = {
    "icm": "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/",
    "imo": "http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/",
    "fun": "http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/",
    "log": "http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/",
    "math": "http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions/",
    "set": "http://tio.models.tmforum.org/tio/v3.6.0/SetOperators/",
}

STANDARD_PREDICATE_PREFIXES = (
    str(RDF),
    str(RDFS),
    "http://www.w3.org/2001/XMLSchema#",
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
    if prefix not in TIO_PREFIXES:
        raise ValueError(f"Unknown prefix in CURIE {curie!r} (supported: {sorted(TIO_PREFIXES)})")
    return URIRef(TIO_PREFIXES[prefix] + name)


def predicate_is_external(p: URIRef) -> bool:
    s = str(p)
    return any(s.startswith(pref) for pref in STANDARD_PREDICATE_PREFIXES)


def case_id_slug(case_id: str) -> str:
    return case_id.strip().lower()


def evaluate_file(
    path: Path,
    ref_classes: set[URIRef],
    ref_properties: set[URIRef],
    expected_elements: list[str],
    case_id: str,
) -> dict:
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
    if parse_error is None:
        for p in set(g.predicates()):
            if not isinstance(p, URIRef):
                continue
            if predicate_is_external(p):
                continue
            if p not in ref_properties:
                unknown_predicates.append(str(p))

    unknown_types: list[str] = []
    if parse_error is None:
        for o in g.objects(None, RDF.type):
            if not isinstance(o, URIRef):
                continue
            if str(o).startswith("http://www.w3.org/"):
                continue
            if o not in ref_classes:
                unknown_types.append(str(o))

    expected_results: list[dict] = []
    if parse_error is None:
        for curie in expected_elements:
            item: dict = {"curie": curie, "ok": False, "reason": ""}
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

    intent_uri_hint_ok = False
    if parse_error is None:
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
        "expected_coverage_ratio": (
            sum(1 for e in expected_results if e.get("ok")) / len(expected_results)
            if expected_results
            else None
        ),
        "intent_uri_contains_case_id": intent_uri_hint_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shared phase-1 evaluator for generated TIO Turtle.")
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

    if not ontology_dir.is_dir():
        print(f"Ontology directory not found: {ontology_dir}", file=sys.stderr)
        return 2
    if not outputs_dir.is_dir():
        print(f"Outputs directory not found: {outputs_dir}", file=sys.stderr)
        return 2
    if not test_cases_path.is_file():
        print(f"Test cases file not found: {test_cases_path}", file=sys.stderr)
        return 2

    ref_classes, ref_properties = load_reference_vocabulary(ontology_dir)
    test_cases = json.loads(test_cases_path.read_text(encoding="utf-8"))
    id_to_case = {tc["id"]: tc for tc in test_cases}

    reports: list[dict] = []
    for tc_id in sorted(id_to_case.keys()):
        ttl_path = outputs_dir / f"{tc_id}.ttl"
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
            )
        )

    print(f"Reference vocabulary: {len(ref_classes)} classes, {len(ref_properties)} properties from {ontology_dir}")
    print()
    for r in reports:
        cid = r["case_id"]
        print(f"=== {cid} ===")
        print(f"  parse_ok: {r['parse_ok']}")
        if not r["parse_ok"] and r.get("parse_error"):
            print(f"  parse_error: {r['parse_error']}")
        if r.get("markdown_fence_stripped"):
            print("  note: stripped ``` markdown fence from file (invalid pure Turtle)")
        if r.get("parse_ok"):
            print(f"  triples: {r['triple_count']}")
            mismatched = [k for k, v in (r.get("prefix_checks") or {}).items() if v.get("matches_official") is False]
            if mismatched:
                print(f"  non_official_prefixes: {', '.join(mismatched)}")
            up = r.get("unknown_predicates") or []
            ut = r.get("unknown_types") or []
            if up:
                print(f"  predicates_not_in_TIO_reference ({len(up)}): {', '.join(up[:5])}{' ...' if len(up) > 5 else ''}")
            if ut:
                print(f"  rdf:type objects_not_in_TIO_reference ({len(ut)}): {', '.join(ut[:5])}{' ...' if len(ut) > 5 else ''}")
            cov = r.get("expected_coverage_ratio")
            if cov is not None:
                print(f"  expected_tio_elements_met: {cov * 100:.0f}%")
            for e in r.get("expected_tio_elements") or []:
                mark = "OK" if e.get("ok") else "MISS"
                print(f"    [{mark}] {e.get('curie')}: {e.get('reason', '')}")
            print(f"  intent_uri_contains_case_id: {r.get('intent_uri_contains_case_id')}")
        print()

    if args.json_out:
        out_path = (root / args.json_out).resolve() if not args.json_out.is_absolute() else args.json_out
        out_path.write_text(json.dumps(reports, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote JSON report to {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
