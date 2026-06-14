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
| operator (comparison fn) | `performance_metrics[].operator` → `quan:smaller`/`atMost`/`greater`/`atLeast`/`exactly` |
| tenant | `tenant` |
| hub / spokes | `scope.hub` / `scope.spokes[]` |
| topology types | `topology{@type,hub_type,spoke_type}` |
| (reference) full vocabulary | `ontology_terms[]` (richer than `expected_tio_elements`) |

### 2.1 Final grounding audit (pre-planning verification)

- **EVSLA is built on the base modules**, so the evaluator's term checks are
  validly grounded: `evsla:EnterpriseVpnSlaIntent ⊑ icm:Intent`,
  `evsla:SlaExpectation ⊑ icm:PropertyExpectation`,
  `evsla:HubAndSpokeTopology/HubSite/SpokeSite ⊑ icm:Context`, the metric
  properties `⊑ met:metric`, the target property `⊑ icm:target`, and
  `evsla:hasThreshold range quan:Quantity`.
- **Comment-implied audit (all 4 few-shot examples):** every semantic element —
  metric, threshold value+unit, statistic, scope, measurement_method, time_window,
  tenant, hub, spokes — is carried by explicit triples using proper icm/met/quan/
  evsla terms. The **only** element living solely in `rdfs:comment` ("must stay
  **below** … / **at least** …") with no triple is the **comparison direction**,
  i.e. the `operator` dimension (§3.1). No other important element is comment-only.
- **"95% of the time"** is fully captured by `evsla:p95` (a `evsla:Statistic`); the
  `met:` Observation/observedValue family is runtime monitoring, outside the intent
  spec's generation target.
- **Nuance:** the test cases' own `ontology_terms[]` lists no `quan:` comparison
  function, so the `operator` dimension is a **deliberate enrichment** derived from
  the gold `operator` field + ontology capability, not from the listed vocabulary —
  consistent with treating it as a currently-0/20 "finding" dimension.

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
| operator | the bound metric's expectation subgraph encodes the comparison direction with the **correct TIO comparison function** per gold `operator` (see §3.1) |

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

### 3.1 `operator` dimension — explicit comparison-function encoding

Gold carries `performance_metrics[].operator`. We score whether the output makes
the comparison direction **explicit** using TIO's comparison vocabulary, rather
than leaving it implied by the metric.

**Evidence this is well-founded** (not a comment-text heuristic):
- `QuantityOntology.ttl` defines a full set of comparison `fun:Function`s (arity 2,
  over `quan:Quantity`, boolean result): `quan:smaller` (<), `quan:greater` (>),
  `quan:atMost` (≤), `quan:atLeast` (≥), `quan:exactly` (=).
- `LogicalOperators.ttl` defines `log:Condition` — the canonical wrapper for a
  boolean condition statement (where such a function is applied).
- `EnterpriseVpnSlaOntology.ttl` **imports `quan:`** (it already uses
  `quan:Quantity` / `quan:unit`), so this comparison vocabulary is legitimately in
  scope for an EVSLA model.

**Gold operator → expected function:**

| gold `operator` | expected function |
|---|---|
| LESS_THAN | `quan:smaller` |
| LESS_THAN_OR_EQUAL | `quan:atMost` |
| GREATER_THAN | `quan:greater` |
| GREATER_THAN_OR_EQUAL | `quan:atLeast` |
| EQUAL | `quan:exactly` |

**Check:** within the bound metric's expectation/target subgraph, the **correct**
comparison-function IRI appears (ideally inside a `log:Condition` / function
application referencing the metric's threshold quantity). Wrong function (e.g.
`quan:atLeast` where `quan:smaller` is expected) → 0; correct → 1; absent → 0. The
check matches the **specific term**, never `rdfs:comment` text.

**Important caveat (a finding, not a bug):** EVSLA's *prescribed* `SlaExpectation`
shape is flat (`evsla:hasThreshold → quan:Quantity`, direction implied by metric)
and does **not** require a comparison function. Verified: all four current
strong-prompt lines use it **0/20**. So under the current strong prompt this
dimension is uniformly 0 across methods — that is itself a reportable result ("no
method models comparison direction explicitly"), and the dimension becomes a
genuine discriminator under weak-prompt + retrieval (does retrieval surface the
`quan:` comparison pattern the prompt never hand-coded?). It is reported as its own
cross-case rate so this 0 is always visible and never silently averaged away.

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
precision 1.5 | measurement_method 1.0 | time_window 1.0 | operator 1.0 |
tenant 1.0 | hub 1.0 | spokes 1.0
```

`operator` is counted in the composite (weight 1.0) but **always reported as its
own cross-case rate** (per §3.1 it is uniformly 0 under the current strong prompt,
so its contribution must stay visible rather than be silently averaged in).

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
    "measurement_method": 1.0, "time_window": 1.0, "operator": 0.0,
    "tenant": 1.0, "hub": 1.0, "spokes": 0.67, "contract": 1.0
  },
  "precision": { "score": 1.0, "hallucination_count": 0 },
  "errors": [ "scope: expected evsla:hubToAllSpokes, got evsla:specificSpoke",
              "spokes: 2/3 matched (missing 北投監控站)" ]
}
```

## 7. Out of scope

- SHACL (graph-binding chosen instead) — no `pyshacl` dependency.
- Changing generation pipelines or the few-shot/prompt — we *score* explicit
  operator encoding if present, but do not change what the prompt teaches the model
  to emit. (Whether to enrich the prompt to teach the `quan:` comparison pattern is
  a separate, downstream decision informed by this evaluator's results.)
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
- `operator`: outputs currently never emit `quan:` comparison functions (0/20), so
  there is no real example of the wiring to anchor on. Implement the check to accept
  the correct comparison-function IRI appearing anywhere in the bound metric's
  expectation/target subgraph (optionally inside a `log:Condition` / function
  application); do not over-specify the exact argument wiring until a real example
  exists. Match the IRI, never `rdfs:comment` text.
