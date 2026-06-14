"""Graph-binding semantic-correctness scoring for TIO Turtle (phase-1).

Pure module (no I/O). `score_semantics(graph, gold_case)` binds each gold metric
to an output subgraph via the intent contract path and scores per-dimension
correctness into a weighted composite. See
docs/superpowers/specs/2026-06-14-stricter-semantic-evaluator-design.md
"""
from __future__ import annotations

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, Namespace

ICM   = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/")
EVSLA = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/")
QUAN  = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/")
MET   = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/")

PREFIXES = {"icm": str(ICM), "evsla": str(EVSLA), "quan": str(QUAN), "met": str(MET)}

# gold operator -> the TIO comparison fun:Function that explicitly encodes direction
OPERATOR_FN = {
    "LESS_THAN": QUAN.smaller,
    "LESS_THAN_OR_EQUAL": QUAN.atMost,
    "GREATER_THAN": QUAN.greater,
    "GREATER_THAN_OR_EQUAL": QUAN.atLeast,
    "EQUAL": QUAN.exactly,
}

WEIGHTS = {
    "metric": 2.0, "threshold": 2.0, "contract": 2.0,
    "scope": 1.5, "statistic": 1.5, "precision": 1.5,
    "measurement_method": 1.0, "time_window": 1.0, "operator": 1.0,
    "tenant": 1.0, "topology": 1.0,
}

METRIC_KEYS = ["metric", "threshold", "statistic", "scope",
               "measurement_method", "time_window", "operator"]


def expand(curie: str) -> URIRef:
    pre, _, local = curie.partition(":")
    return URIRef(PREFIXES[pre] + local)


def _obj(g, s, p):
    for o in g.objects(s, p):
        return o
    return None


def _threshold(g, target):
    for p in (EVSLA.hasThreshold, ICM.valuesOfTargetProperty):
        q = _obj(g, target, p)
        if q is not None:
            val = _obj(g, q, RDF.value)
            if val is not None:
                return val, _obj(g, q, QUAN.unit)
    return None, None


def _subgraph_terms(g, root, depth=5):
    """All predicates + URIRef objects reachable from root up to `depth` hops."""
    seen, frontier = set(), [root]
    while frontier and depth >= 0:
        nxt = []
        for n in frontier:
            for p, o in g.predicate_objects(n):
                seen.add(p)
                if isinstance(o, URIRef):
                    seen.add(o)
                nxt.append(o)
        frontier, depth = nxt, depth - 1
    return seen


def extract_bindings(g):
    """Metric bindings reachable from any icm:Intent via the contract path."""
    bindings = []
    for intent in g.subjects(RDF.type, ICM.Intent):
        for el in g.objects(intent, ICM.intentElements):
            types = set(g.objects(el, RDF.type))
            if ICM.PropertyExpectation not in types and EVSLA.SlaExpectation not in types:
                continue
            target = _obj(g, el, ICM.target)
            if target is None:
                bindings.append({"expectation": el, "target": None, "metric": None})
                continue
            bindings.append({
                "expectation": el, "target": target,
                "metric": _obj(g, target, EVSLA.hasMetric),
                "statistic": _obj(g, target, EVSLA.hasStatistic),
                "scope": _obj(g, target, EVSLA.hasScope),
                "method": _obj(g, target, EVSLA.hasMeasurementMethod),
                "time_window": _obj(g, target, EVSLA.hasTimeWindow),
            })
    return bindings


def _eq(node, curie):
    return node is not None and node == expand(curie)


def _tenant_ok(g, gold):
    want = gold.get("tenant", "")
    for t in g.subjects(RDF.type, EVSLA.Tenant):
        for lbl in g.objects(t, RDFS.label):
            if str(lbl) == want:
                return 1.0
    return 0.0


def _topology_ok(g):
    if not list(g.subjects(RDF.type, EVSLA.HubAndSpokeTopology)):
        return 0.0
    has_hub = next(g.subjects(RDF.type, EVSLA.HubSite), None) is not None
    has_spoke = next(g.subjects(RDF.type, EVSLA.SpokeSite), None) is not None
    return 1.0 if (has_hub and has_spoke) else 0.0


def _score_one_metric(g, pm, bindings, errors):
    want = expand(pm["ontology_term"])
    b = next((x for x in bindings if x.get("metric") == want), None)
    d = {k: 0.0 for k in METRIC_KEYS}
    if b is None:
        errors.append(f"metric {pm['ontology_term']}: no reachable target")
        return d
    d["metric"] = 1.0
    val, unit = _threshold(g, b["target"])
    tv = val is not None and float(val) == float(pm["threshold"]["value"])
    tu = unit is not None and str(unit) == str(pm["threshold"]["unit"])
    d["threshold"] = 1.0 if (tv and tu) else 0.0
    if not (tv and tu):
        errors.append(f"threshold {pm['ontology_term']}: expected "
                      f"{pm['threshold']['value']} {pm['threshold']['unit']}, got {val} {unit}")
    for key, attr in [("statistic", "statistic"), ("scope", "scope"),
                      ("measurement_method", "method"), ("time_window", "time_window")]:
        ok = _eq(b.get(attr), pm[key])
        d[key] = 1.0 if ok else 0.0
        if not ok:
            errors.append(f"{key} {pm['ontology_term']}: expected {pm[key]}, got {b.get(attr)}")
    expected_fn = OPERATOR_FN.get(pm.get("operator"))
    d["operator"] = 1.0 if expected_fn in _subgraph_terms(g, b["expectation"]) else 0.0
    return d


def score_semantics(g, gold):
    bindings = extract_bindings(g)
    pms = gold.get("performance_metrics", [])
    gold_iris = {expand(pm["ontology_term"]) for pm in pms}
    errors = []
    per = [_score_one_metric(g, pm, bindings, errors) for pm in pms]

    dims = {}
    for k in METRIC_KEYS:
        vals = [d[k] for d in per]
        dims[k] = sum(vals) / len(vals) if vals else 0.0
    dims["tenant"] = _tenant_ok(g, gold)
    dims["topology"] = _topology_ok(g)

    reachable = {b.get("metric") for b in bindings}
    dims["contract"] = (sum(1 for mi in gold_iris if mi in reachable) / len(gold_iris)
                        if gold_iris else 0.0)

    out_bindings = [b for b in bindings if b.get("metric") is not None]
    matched = sum(1 for b in out_bindings if b["metric"] in gold_iris)
    total = len(out_bindings)
    dims["precision"] = matched / total if total else 1.0
    hallucination = total - matched

    composite = sum(WEIGHTS[k] * dims[k] for k in WEIGHTS) / sum(WEIGHTS.values())
    return {
        "composite": round(composite, 4),
        "dimensions": {k: round(v, 4) for k, v in dims.items()},
        "precision": {"score": round(dims["precision"], 4), "hallucination_count": hallucination},
        "errors": errors,
    }
