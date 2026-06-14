# Stricter Semantic Evaluator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a graph-binding semantic-correctness layer to the phase-1 evaluator so the four TIO-generation lines can be ranked on whether they model the *right* values/terms/wiring, not just presence.

**Architecture:** A new pure module `semantic_eval.py` binds each gold metric (from `test_cases_20.json`) to an output subgraph by traversing the intent→intentElements→expectation→target→hasMetric contract path, then scores per-dimension correctness into a weighted composite. `evaluate_ttl.py` calls it post-parse and merges a `semantic` block; `compare_reports.py` adds a Semantic Summary.

**Tech Stack:** Python 3.13, rdflib 7.x, unittest.

**Spec:** `docs/superpowers/specs/2026-06-14-stricter-semantic-evaluator-design.md`

**Dimensions (11):** metric, threshold, statistic, scope, measurement_method, time_window, operator, tenant, topology, contract, precision. (Spec's hub+spokes name-match → one structural `topology` dim; see plan header note.)

---

## File Structure

- Create `semantic_eval.py` — pure scoring module (no I/O).
- Create `test_semantic_eval.py` — unittest over crafted graphs.
- Modify `evaluate_ttl.py` — pass full gold case to `evaluate_file`, attach `semantic` block post-parse.
- Modify `compare_reports.py` — add Semantic Summary block.

---

### Task 1: semantic_eval scaffolding — namespaces, weights, curie/operator maps

**Files:**
- Create: `semantic_eval.py`
- Test: `test_semantic_eval.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest
from semantic_eval import expand, OPERATOR_FN, WEIGHTS, QUAN

class TestScaffold(unittest.TestCase):
    def test_expand_curie(self):
        self.assertEqual(str(expand("evsla:latency")),
            "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/latency")
    def test_operator_map(self):
        self.assertEqual(OPERATOR_FN["LESS_THAN"], QUAN.smaller)
        self.assertEqual(OPERATOR_FN["GREATER_THAN_OR_EQUAL"], QUAN.atLeast)
    def test_weights_keys(self):
        self.assertEqual(set(WEIGHTS), {
            "metric","threshold","statistic","scope","measurement_method",
            "time_window","operator","tenant","topology","contract","precision"})

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_semantic_eval -v`
Expected: FAIL (ModuleNotFoundError: semantic_eval).

- [ ] **Step 3: Write minimal implementation**

```python
"""Graph-binding semantic-correctness scoring for TIO Turtle (phase-1)."""
from __future__ import annotations
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, Namespace

ICM   = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/")
EVSLA = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/")
QUAN  = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/")
MET   = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/")

PREFIXES = {"icm": str(ICM), "evsla": str(EVSLA), "quan": str(QUAN), "met": str(MET)}

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

def expand(curie: str) -> URIRef:
    pre, _, local = curie.partition(":")
    return URIRef(PREFIXES[pre] + local)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_semantic_eval -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add semantic_eval.py test_semantic_eval.py
git commit -m "feat(eval): semantic_eval scaffolding (namespaces, weights, operator map)"
```

---

### Task 2: Binding extraction + helpers

**Files:**
- Modify: `semantic_eval.py`
- Test: `test_semantic_eval.py`

- [ ] **Step 1: Write the failing test** (append to test file)

```python
from rdflib import Graph
from semantic_eval import extract_bindings, EVSLA

GOOD_TTL = """
@prefix icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .
@prefix quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex:    <http://example.org/tio-instance/tc001/> .
ex:intent a icm:Intent, evsla:EnterpriseVpnSlaIntent ;
  icm:intentElements ex:exp-latency, ex:topology .
ex:tenant a evsla:Tenant ; rdfs:label "星河銀行"@zh .
ex:exp-latency a icm:PropertyExpectation, evsla:SlaExpectation ; icm:target ex:tgt-latency .
ex:tgt-latency a icm:Target ;
  evsla:hasMetric evsla:latency ;
  evsla:hasThreshold [ a quan:Quantity ; rdf:value 50 ; quan:unit "ms" ] ;
  evsla:hasStatistic evsla:p95 ; evsla:hasScope evsla:hubToAllSpokes ;
  evsla:hasMeasurementMethod evsla:twamp ; evsla:hasTimeWindow evsla:fiveMinuteWindow .
ex:topology a icm:Context, evsla:HubAndSpokeTopology ;
  evsla:hasHub [ a evsla:HubSite ; rdfs:label "總部"@zh ] ;
  evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label "所有分點"@zh ] .
"""

class TestBindings(unittest.TestCase):
    def test_extract_one_binding(self):
        g = Graph(); g.parse(data=GOOD_TTL, format="turtle")
        b = extract_bindings(g)
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0]["metric"], EVSLA.latency)
        self.assertEqual(b[0]["scope"], EVSLA.hubToAllSpokes)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_semantic_eval.TestBindings -v`
Expected: FAIL (cannot import name 'extract_bindings').

- [ ] **Step 3: Write minimal implementation** (append to `semantic_eval.py`)

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_semantic_eval -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add semantic_eval.py test_semantic_eval.py
git commit -m "feat(eval): contract-path binding extraction"
```

---

### Task 3: score_semantics — full scoring + composite

**Files:**
- Modify: `semantic_eval.py`
- Test: `test_semantic_eval.py`

- [ ] **Step 1: Write the failing test** (append; reuses GOOD_TTL)

```python
from semantic_eval import score_semantics

GOLD_TC001 = {
    "tenant": "星河銀行",
    "performance_metrics": [{
        "operator": "LESS_THAN", "threshold": {"value": 50, "unit": "ms"},
        "ontology_term": "evsla:latency", "statistic": "evsla:p95",
        "scope": "evsla:hubToAllSpokes", "measurement_method": "evsla:twamp",
        "time_window": "evsla:fiveMinuteWindow",
    }],
}

class TestScore(unittest.TestCase):
    def test_correct_graph_scores_high(self):
        g = Graph(); g.parse(data=GOOD_TTL, format="turtle")
        r = score_semantics(g, GOLD_TC001)
        d = r["dimensions"]
        self.assertEqual(d["metric"], 1.0)
        self.assertEqual(d["threshold"], 1.0)
        self.assertEqual(d["statistic"], 1.0)
        self.assertEqual(d["scope"], 1.0)
        self.assertEqual(d["tenant"], 1.0)
        self.assertEqual(d["topology"], 1.0)
        self.assertEqual(d["contract"], 1.0)
        self.assertEqual(d["operator"], 0.0)            # no quan:smaller emitted
        self.assertEqual(r["precision"]["hallucination_count"], 0)
        self.assertGreater(r["composite"], 0.85)

    def test_wrong_scope_and_value_penalised(self):
        bad = GOOD_TTL.replace("evsla:hubToAllSpokes", "evsla:specificSpoke") \
                      .replace("rdf:value 50", "rdf:value 999")
        g = Graph(); g.parse(data=bad, format="turtle")
        d = score_semantics(g, GOLD_TC001)["dimensions"]
        self.assertEqual(d["scope"], 0.0)
        self.assertEqual(d["threshold"], 0.0)
        self.assertEqual(d["metric"], 1.0)

    def test_hallucinated_extra_metric(self):
        extra = GOOD_TTL.replace("icm:intentElements ex:exp-latency, ex:topology .",
            "icm:intentElements ex:exp-latency, ex:exp-bw, ex:topology .") + """
ex:exp-bw a icm:PropertyExpectation, evsla:SlaExpectation ; icm:target ex:tgt-bw .
ex:tgt-bw a icm:Target ; evsla:hasMetric evsla:guaranteedBandwidth .
"""
        g = Graph(); g.parse(data=extra, format="turtle")
        r = score_semantics(g, GOLD_TC001)
        self.assertEqual(r["precision"]["hallucination_count"], 1)
        self.assertLess(r["dimensions"]["precision"], 1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_semantic_eval.TestScore -v`
Expected: FAIL (cannot import name 'score_semantics').

- [ ] **Step 3: Write minimal implementation** (append to `semantic_eval.py`)

```python
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

METRIC_KEYS = ["metric", "threshold", "statistic", "scope",
               "measurement_method", "time_window", "operator"]

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
    for key, gkey, attr in [
        ("statistic", "statistic", "statistic"),
        ("scope", "scope", "scope"),
        ("measurement_method", "measurement_method", "method"),
        ("time_window", "time_window", "time_window"),
    ]:
        ok = _eq(b.get(attr), pm[gkey])
        d[key] = 1.0 if ok else 0.0
        if not ok:
            errors.append(f"{key} {pm['ontology_term']}: expected {pm[gkey]}, got {b.get(attr)}")
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_semantic_eval -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add semantic_eval.py test_semantic_eval.py
git commit -m "feat(eval): score_semantics per-dimension + weighted composite"
```

---

### Task 4: Integrate into evaluate_ttl.py

**Files:**
- Modify: `evaluate_ttl.py` (`evaluate_file` signature + return; `evaluate_experiment` call site)

- [ ] **Step 1: Add import and pass gold case**

At top of `evaluate_ttl.py` imports add:
```python
from semantic_eval import score_semantics
```
Change `evaluate_file` signature to accept the full case and attach the block. In `evaluate_file`, just before the final `return {`, insert:
```python
    semantic = (score_semantics(g, gold_case)
                if (parse_error is None and gold_case) else None)
```
Add `gold_case: dict | None = None` as the last parameter of `evaluate_file`, and add `"semantic": semantic,` as the last key of the returned dict.

- [ ] **Step 2: Update the call site**

In `evaluate_experiment`, change:
```python
    reports.append(evaluate_file(path, tc.get("expected_tio_elements", []), tc_id))
```
to:
```python
    reports.append(evaluate_file(path, tc.get("expected_tio_elements", []), tc_id, gold_case=tc))
```

- [ ] **Step 3: Run evaluator on a real line and verify the block appears**

Run:
```bash
python3 evaluate_ttl.py graphrag
python3 -c "import json; d=json.load(open('phase1/phase1_graphrag.json')); print(json.dumps(d[0]['semantic'], ensure_ascii=False, indent=1))"
```
Expected: a `semantic` object with `composite`, `dimensions` (11 keys), `precision`, `errors`.

- [ ] **Step 4: Commit**

```bash
git add evaluate_ttl.py
git commit -m "feat(eval): attach semantic block to phase-1 reports"
```

---

### Task 5: Semantic Summary in compare_reports.py

**Files:**
- Modify: `compare_reports.py` (`emit_report` adds a Semantic Summary block)

- [ ] **Step 1: Add the aggregation + print function**

Add to `compare_reports.py` (after `print_overall`):
```python
SEM_DIMS = ["metric","threshold","statistic","scope","measurement_method",
            "time_window","operator","tenant","topology","contract","precision"]

def print_semantic(reports):
    print_header("Semantic Summary (graph-binding correctness)")
    header = f"{'Experiment':14} | {'Composite':9} | " + " | ".join(f"{d[:5]:>5}" for d in SEM_DIMS)
    print(header); print("-" * len(header))
    for name, _, items in reports:
        sem = [x.get("semantic") for x in items if x.get("semantic")]
        n = len(sem) or 1
        comp = sum(s["composite"] for s in sem) / n
        rates = [sum(s["dimensions"].get(d, 0.0) for s in sem) / n for d in SEM_DIMS]
        print(f"{name:14} | {comp:9.4f} | " + " | ".join(f"{r:5.2f}" for r in rates))
```
Then in `emit_report`, after `print_overall(reports)` add:
```python
    print_semantic(reports)
```

- [ ] **Step 2: Run the comparison and verify the block renders**

Run: `python3 compare_reports.py`
Expected: a "Semantic Summary" table with a Composite column + 11 dimension columns for all 4 lines.

- [ ] **Step 3: Commit**

```bash
git add compare_reports.py
git commit -m "feat(eval): semantic summary in four-way comparison"
```

---

### Task 6: End-to-end run + record results

**Files:** none (run only)

- [ ] **Step 1: Re-evaluate all four lines and rebuild comparison**

Run:
```bash
python3 run_all_experiments.py --eval-only
```
Expected: all four `phase1/phase1_*.json` regenerated with `semantic` blocks; `phase1/output_quality/compare_four_way.txt` now includes the Semantic Summary.

- [ ] **Step 2: Run the full unit suite**

Run: `python3 -m unittest test_semantic_eval -v`
Expected: PASS.

- [ ] **Step 3: Inspect and report the semantic ranking** (show the Semantic Summary block to the user).

---

## Self-Review notes

- **Spec coverage:** dimensions metric/threshold/statistic/scope/method/time_window/operator/tenant/contract/precision implemented in Task 3; topology replaces spec hub+spokes (header note); composite+weights Task 3; augment-not-replace Task 4; Semantic Summary Task 5; gold from test_cases_20.json via `gold_case=tc` Task 4.
- **Operator:** matched by IRI via `_subgraph_terms` (never comment text); expected 0/20 on current outputs.
- **Type consistency:** `score_semantics`, `extract_bindings`, `expand`, `OPERATOR_FN`, `WEIGHTS` names identical across tasks; dimension key set identical in `WEIGHTS`, `score_semantics`, `SEM_DIMS`.
