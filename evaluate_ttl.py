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

from semantic_eval import score_semantics

ROOT = Path(__file__).resolve().parent
ONTOLOGY_DIR = ROOT / "TM Forum Intent Ontology"

FUN = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/")

TIO_PREFIXES = {
    "icm": "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/",
    "imo": "http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/",
    "fun": "http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/",
    "log": "http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/",
    "math": "http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions/",
    "set": "http://tio.models.tmforum.org/tio/v3.6.0/SetOperators/",
    "evsla": "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/",
    "quan": "http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/",
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


_REFERENCE_VOCAB: tuple[set[URIRef], set[URIRef]] | None = None


def reference_vocabulary() -> tuple[set[URIRef], set[URIRef]]:
    """Load (and cache) the TIO reference vocabulary from ONTOLOGY_DIR."""
    global _REFERENCE_VOCAB
    if _REFERENCE_VOCAB is None:
        _REFERENCE_VOCAB = load_reference_vocabulary(ONTOLOGY_DIR)
    return _REFERENCE_VOCAB


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
    expected_elements: list[str],
    case_id: str,
    ref_classes: set[URIRef] | None = None,
    ref_properties: set[URIRef] | None = None,
    gold_case: dict | None = None,
) -> dict:
    if ref_classes is None or ref_properties is None:
        ref_classes, ref_properties = reference_vocabulary()

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

    semantic = (score_semantics(g, gold_case)
                if (parse_error is None and gold_case) else None)

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
        "semantic": semantic,
    }


EXPERIMENTS = {
    "llm_only": {"label": "LLM-only", "outputs_dir": ROOT / "tio_outputs" / "llm_only",
                 "report": ROOT / "phase1" / "phase1_llm_only.json"},
    "graphrag": {"label": "GraphRAG", "outputs_dir": ROOT / "tio_outputs" / "graphrag",
                 "report": ROOT / "phase1" / "phase1_graphrag.json"},
    "kge": {"label": "KGE", "outputs_dir": ROOT / "tio_outputs" / "kge",
            "report": ROOT / "phase1" / "phase1_kge.json"},
    "kag": {"label": "KAG", "outputs_dir": ROOT / "tio_outputs" / "kag",
            "report": ROOT / "phase1" / "phase1_kag.json"},
    "llm_only_weak": {"label": "LLM-only-weak", "outputs_dir": ROOT / "tio_outputs" / "llm_only_weak",
                      "report": ROOT / "phase1" / "phase1_llm_only_weak.json"},
    "graphrag_weak": {"label": "GraphRAG-weak", "outputs_dir": ROOT / "tio_outputs" / "graphrag_weak",
                      "report": ROOT / "phase1" / "phase1_graphrag_weak.json"},
    "kge_weak": {"label": "KGE-weak", "outputs_dir": ROOT / "tio_outputs" / "kge_weak",
                 "report": ROOT / "phase1" / "phase1_kge_weak.json"},
    "kag_weak": {"label": "KAG-weak", "outputs_dir": ROOT / "tio_outputs" / "kag_weak",
                 "report": ROOT / "phase1" / "phase1_kag_weak.json"},
}


def test_cases_path() -> Path:
    return ROOT / "test_cases_20.json"


def evaluate_experiment(experiment_key: str, test_cases: list[dict]) -> Path:
    config = EXPERIMENTS[experiment_key]
    outputs_dir = config["outputs_dir"]
    reports = []
    for tc in test_cases:
        tc_id = tc["id"]
        path = outputs_dir / f"{tc_id}.ttl"
        if not path.is_file():
            reports.append({"case_id": tc_id, "parse_ok": False,
                            "parse_error": f"missing file: {path}",
                            "triple_count": 0, "expected_results": [],
                            "expected_coverage_ratio": None})
            continue
        reports.append(evaluate_file(path, tc.get("expected_tio_elements", []), tc_id, gold_case=tc))

    print(f"\n## {config['label']}")
    for row in reports:
        print(f"=== {row['case_id']} ===")
        print(f"  parse_ok: {row['parse_ok']}")
        if row.get("parse_error"):
            print(f"  parse_error: {row['parse_error']}")
        cov = row.get("expected_coverage_ratio")
        if cov is not None:
            print(f"  expected_tio_elements_met: {cov * 100:.0f}%")
    report_path = config["report"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(reports, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote JSON report to {report_path}")
    return report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shared phase-1 evaluator for generated TIO Turtle.")
    parser.add_argument("experiment", nargs="?",
                        choices=tuple(EXPERIMENTS.keys()) + ("all",), default="all")
    args = parser.parse_args(argv)
    cases = json.loads(test_cases_path().read_text(encoding="utf-8"))
    keys = list(EXPERIMENTS.keys()) if args.experiment == "all" else [args.experiment]
    for key in keys:
        evaluate_experiment(key, cases)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
