# Stricter Semantic Evaluator — Design Spec

**Date:** 2026-06-14
**Author:** 睿丞 (with Claude Code)
**Status:** Approved design — pending implementation plan

## 1. Purpose

The current `evaluate_ttl.py` checks only syntax (parse), out-of-vocabulary
terms, intent-URI naming, and **existence** of ~5 high-level skeleton
classes/properties (`expected_tio_elements`). Under the strong prompt that
hand-codes the EVSLA skeleton, every line trivially hits all of these → all four
lines score ~100% and cannot be ranked. The evaluator is a *format + vocabulary +
skeleton-presence* check, explicitly not a *semantic-correctness* check
(CLAUDE.md §4.5 admits this; progress.md Next Steps §4 flags it).

This evaluator adds a **semantic-correctness layer** that verifies the generated
Turtle actually models the *right* values, terms, and graph wiring against the
per-case ground truth — so retrieval methods can be ranked on correctness, not
just presence. It is the complement to the weak-prompt experiment: the weak
prompt creates variance; this evaluator makes the variance meaningful.

## 2. Gold source — embedded in `test_cases_20.json`

No separate gold file. The structured per-case fields already in
`test_cases_20.json` are the ground truth (verified complete for all 20 cases;
TC020 is the only multi-metric case, 2 metrics). The evaluator reads them
directly. These fields are **eval-only** — generation pipelines read only
`nl_intent`, so there is no train/test leakage.

Field → dimension mapping:

| Dimension | Gold field |
|---|---|
| metric | `performance_metrics[].ontology_term` |
| threshold value + unit | `performance_metrics[].threshold{value,unit}` |
| statistic | `performance_metrics[].statistic` |
| scope | `performance_metrics[].scope` |
| measurement_method | `performance_metrics[].measurement_method` |
| time_window | `performance_metrics[].time_window` |
| tenant | `tenant` |
| hub / spokes | `scope.hub` / `scope.spokes[]` |
| topology types | `topology{@type,hub_type,spoke_type}` |
| (reference) full vocabulary | `ontology_terms[]` (richer than `expected_tio_elements`) |

## 3. Verification — graph-binding semantic check

Match each gold metric to an output subgraph by **traversing the contract path
from the intent**, then verify *that bound node's* attributes. Traversal both
locates the node and validates wiring.

**Binding algorithm** (over the parsed rdflib graph `g`):
1. Locate the intent: subject typed `icm:Intent`.
2. Traverse `intent --icm:intentElements--> {elements}`; keep expectations
   (typed `icm:PropertyExpectation` / `evsla:SlaExpectation`).
3. For each expectation: `--icm:target--> Target`, then read
   `Target --evsla:hasMetric--> metricIRI` plus the Target's threshold /
   statistic / scope / measurement_method / time_window.
4. This yields a list of **output bindings**: `(expectation, target, metricIRI, attrs)`.
5. For each **gold** metric, find the output binding whose `metricIRI` equals the
   gold `ontology_term`:
   - **Found & reachable via the path** → score its attribute dimensions against gold; `contract` = ok.
   - **Not found, or a matching Target exists but is not reachable from the intent
     via the path** → `metric` = 0, its dependent attribute dimensions = 0,
     `contract` = fail (records "disconnected" vs "missing").

**Per-metric dimensions** (scored on the bound Target):

| Dimension | Check |
|---|---|
| metric | `evsla:hasMetric` == gold `ontology_term` |
| threshold | a `quan:Quantity` (via `evsla:hasThreshold` and/or `icm:valuesOfTargetProperty`) with `rdf:value` == gold value (numeric, int/float tolerant) **and** `quan:unit` == gold unit (normalized string) |
| statistic | `evsla:hasStatistic` == gold |
| scope | `evsla:hasScope` == gold |
| measurement_method | `evsla:hasMeasurementMethod` == gold |
| time_window | `evsla:hasTimeWindow` == gold |

**Case-level dimensions:**

| Dimension | Check |
|---|---|
| tenant | an `evsla:Tenant` node whose `rdfs:label` matches gold `tenant` |
| hub | an `evsla:HubSite` whose label matches gold `scope.hub` |
| spokes | `evsla:SpokeSite` nodes vs gold `scope.spokes[]` — ratio of matched names (count + identity) |
| contract / wiring | the intent→intentElements→expectation→target→Target(→hasMetric) path is intact for each expected metric; tenant linked via `evsla:EnterpriseVpnService` / `evsla:forTenant` |
| precision | of all output bindings, the fraction that map to a gold metric; also report `hallucination_count` = output bindings matching no gold metric (extra/contradictory expectations) |

**Label matching:** normalized exact match (strip language tag, exact string;
Chinese names literal). Fuzzy matching is out of scope (future).

### 3.1 Why `operator` is excluded (deliberate, not an oversight)

Gold carries `performance_metrics[].operator` (LESS_THAN / GREATER_THAN_OR_EQUAL),
but it is **not a scored dimension**, because:

1. The experiment's own canonical gold shape does not encode it — the few-shot
   reference (`FS-EVSLA-01`), the prompt template, and every output express the
   threshold as a `quan:Quantity` (value + unit) and leave direction **implied by
   the metric** (latency ⇒ below; guaranteedBandwidth ⇒ at least). Scoring an
   operator triple would penalize output that correctly conforms to the gold shape.
2. Its semantic content (direction) is one-to-one with the metric
   (`evsla:latency` ⟺ LESS_THAN, `evsla:guaranteedBandwidth` ⟺ GREATER_THAN_OR_EQUAL),
   so it is **transitively covered by the `metric` dimension** — choosing the
   wrong metric flips the direction and is already penalized.

Making TIO output carry an explicit operator would be a change to the *gold shape*
(touching few-shot / prompt), a separate decision outside this evaluator.

## 4. Scoring model — per-dimension sub-scores + weighted composite

- Each dimension yields `0/1` per case (spokes yields a ratio).
- For multi-metric cases (TC020), per-metric dimensions are averaged across the
  case's metrics before combining with case-level dimensions.
- **Per-case composite** = `Σ(weight_d · score_d) / Σ weight_d`.
- **Headline `semantic_score`** = mean composite across the 20 cases.
- Each dimension is also reported as a **cross-case correctness rate** (e.g.,
  "scope correct 18/20") — this is the diagnostic that shows *where* a method fails.

**Default weights** (module-level `WEIGHTS` constant, tunable):

```
metric 2.0 | threshold 2.0 | contract 2.0 | scope 1.5 | statistic 1.5 |
precision 1.5 | measurement_method 1.0 | time_window 1.0 |
tenant 1.0 | hub 1.0 | spokes 1.0
```

Weights are a starting point, not load-bearing for the architecture; they live in
one constant so they can be re-tuned without touching logic.

## 5. Architecture — augment, don't replace

- **New module `semantic_eval.py`** — pure function
  `score_semantics(graph, gold_case) -> dict` returning per-dimension scores, the
  per-case composite, the precision block, and a **diagnostic `errors` list**
  (e.g., `"scope: expected evsla:hubToAllSpokes, got evsla:specificSpoke"`,
  `"threshold unit: expected ms, got Mbps"`, `"metric evsla:latency: target not
  reachable from intent"`). No I/O; independently unit-testable.
- **`evaluate_ttl.py`** — after a successful parse (the existing `parse_ok` gate),
  call `score_semantics` with the matching full test-case dict and merge the result
  into the per-case report under a `semantic` key. On parse failure, `semantic` =
  `null`. All existing basic fields (parse_ok, unknown vocab, intent_uri,
  expected_coverage) are **retained** as preconditions / basic gates.
- **`compare_reports.py`** — add a "Semantic Summary" block: the composite
  `semantic_score` plus key per-dimension rates (metric / threshold / scope /
  statistic / contract / precision). The existing basic summary stays.

## 6. Output schema (per case, added)

```jsonc
"semantic": {
  "composite": 0.86,
  "dimensions": {
    "metric": 1.0, "threshold": 1.0, "statistic": 1.0, "scope": 0.0,
    "measurement_method": 1.0, "time_window": 1.0,
    "tenant": 1.0, "hub": 1.0, "spokes": 0.67, "contract": 1.0
  },
  "precision": { "score": 1.0, "hallucination_count": 0 },
  "errors": [ "scope: expected evsla:hubToAllSpokes, got evsla:specificSpoke",
              "spokes: 2/3 matched (missing 北投監控站)" ]
}
```

## 7. Out of scope

- SHACL (graph-binding chosen instead) — no `pyshacl` dependency.
- Changing generation pipelines or the gold shape (operator stays implicit).
- Re-deriving/curating gold (reuse existing `test_cases_20.json` fields).
- Fuzzy label matching (normalized exact only this round).

## 8. Relationship to the weak-prompt experiment

Build this evaluator **first**, then run the weak-prompt experiment under it, so
weak-prompt results are measured with semantic scoring from the start (no re-eval).
The two specs are complementary:
`docs/superpowers/specs/2026-06-13-weak-prompt-retrieval-substitution-design.md`.

## 9. Affected files

- new `semantic_eval.py` — binding + per-dimension scoring + diagnostics (pure).
- `evaluate_ttl.py` — call `score_semantics` post-parse, merge `semantic` block,
  pass full test-case dict (not just `expected_tio_elements`).
- `compare_reports.py` — add Semantic Summary block (composite + key dim rates).
- (tests) `test_semantic_eval.py` — unit tests over crafted graphs (correct,
  wrong-scope, wrong-value, mis-wired, hallucinated-extra).

## 10. Open implementation flags (verify during build, not placeholders)

- Confirm `evsla:hasThreshold` vs `icm:valuesOfTargetProperty` carry the
  `quan:Quantity`; accept either as the threshold source.
- Blank-node vs URI `quan:Quantity` — rdflib traversal handles both; ensure code
  does not assume URIRef.
- Confirm the `evsla:EnterpriseVpnService` / `evsla:forTenant` linkage is present
  in outputs for the tenant-wiring check; if absent across all lines, treat tenant
  wiring as label-only (do not penalize uniformly).
