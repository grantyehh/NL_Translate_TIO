# GraphRAG Domain-Graph Redesign + Structure-Only Evaluation

Date: 2026-06-15

Status: design approved, pending spec review

## 1. Research Question

The current experiment cannot tell retrieval methods apart from prompt
engineering. Under the strong prompt, all four lines saturate the evaluator;
under the weak prompt (no domain knowledge at all), all retrieval lines score
0 because they are an all-or-nothing floor with no scaffolding.

This redesign asks the sharper, fairer question:

> When the system prompt supplies the **assembly architecture** (the Turtle
> skeleton and the condition pattern) but withholds **all EVSLA vocabulary**
> (namespace IRIs, metric/statistic/scope/method/window mappings, operator
> terms), can a methodologically legitimate GraphRAG retrieve that vocabulary
> well enough to recover quality — at a token cost far below the current
> ~13.5k/case — and does it beat a no-retrieval control?

The redesign is scoped to **GraphRAG** and lives in `TIO_Experiment` (this
repo, Turtle pipeline). KGE is reused as a comparison line but is not
redesigned here.

## 2. Background and Motivating Evidence

Two diagnoses from prior work drive this design:

1. **Wrong slice + bad serialization (Experiment 1 GraphRAG).** The old
   `typed_bfs_subgraph` walked only `rdf:type` / `subClassOf` / `domain` /
   `range` — the TBox plumbing — and serialized CURIEs with **no `@prefix`
   declarations**, so the model could not resolve terms to official IRIs.
2. **The bloat moves, it does not disappear (Experiment 2 smoke, n=1, TC101).**
   The Experiment 2 redesign added an `@prefix` block (mechanically correct)
   but replaced the BFS blast with a large "Asserted RDF schema facts" dump.
   Result: GraphRAG used **13,546 retrieval tokens** (KGE: 118), scored the
   **worst `ontology_validity` (0.05)**, and lost to KGE on quality. Retrieval
   did add value over the structure-only control (information gain +0.16
   GraphRAG, +0.38 KGE) but neither approached the full prompt.

Conclusion carried into this design: the useful retrieval signal is a **small,
query-specific set of term→URI bindings plus the closed vocabulary per slot**,
not a schema-fact dump. Methodologically, a legitimate GraphRAG over an
existing ontology must do entry-point retrieval plus **bounded traversal of
meaningful relationships**, explicitly **excluding the structural plumbing
edges** (this mirrors graphrag.com's Graph-Enhanced Vector Search, which
excludes `HAS_ENTITY` / `PART_OF`).

## 3. GraphRAG Method Positioning

This is an **Ontology-Aware Domain-Graph RAG** over the frozen TIO / EVSLA RDF
ontology:

```text
natural-language intent
  -> lexical + vector entry-point grounding
  -> bounded traversal of meaningful EVSLA/ICM connective object-properties
  -> role-scoped closed vocabulary attachment
  -> serialized, self-contained context (@prefix + grounded terms + relations + closed vocab)
  -> Turtle generation under a structure-only prompt
```

It is genuinely graph-based (traversal of the property graph, not a taxonomy
dump) and is distinct from KGE (no embeddings-of-graph, no TransE, no link
prediction) and from plain vector RAG (traversal contributes the relational
wiring and the closed per-role vocabulary). It is **not** Microsoft GraphRAG:
no document chunking, no LLM entity/relationship extraction, no community
detection, no global search. It returns only facts asserted in the bundled
ontology; it does not materialize RDFS/OWL closure.

## 4. Ontology Facts This Design Relies On (verified)

**Connective object-properties (the meaningful edges traversal follows):**

| property | domain | range |
|---|---|---|
| `evsla:hasMetric` | `evsla:SlaExpectation` | `rdf:Property` (a metric) |
| `evsla:hasThreshold` | `evsla:SlaExpectation` | `quan:Quantity` |
| `evsla:hasStatistic` | `evsla:SlaExpectation` | `evsla:Statistic` |
| `evsla:hasScope` | `evsla:SlaExpectation` | `evsla:Scope` |
| `evsla:hasMeasurementMethod` | `evsla:SlaExpectation` | `evsla:MeasurementMethod` |
| `evsla:hasTimeWindow` | `evsla:SlaExpectation` | `evsla:TimeWindow` |
| `evsla:hasHub` | `evsla:HubAndSpokeTopology` | `evsla:HubSite` |
| `evsla:hasSpoke` | `evsla:HubAndSpokeTopology` | `evsla:SpokeSite` |
| `evsla:forTenant` | (expectation context) | `evsla:Tenant` |
| (service link) | `icm:Expectation` | `evsla:EnterpriseVpnService` |
| (topology link) | — | `evsla:HubAndSpokeTopology` |

**Closed role vocabularies (the per-slot legal value sets):**

- Metric (`rdfs:subPropertyOf met:metric`): `evsla:latency`, `evsla:packetLoss`,
  `evsla:guaranteedBandwidth`
- Statistic (`a evsla:Statistic`): `evsla:p95`, `evsla:p99`, `evsla:average`,
  `evsla:maximum`, `evsla:minimum`
- Scope (`a evsla:Scope`): `evsla:hubToAllSpokes`, `evsla:perSpoke`,
  `evsla:specificSpoke`
- MeasurementMethod (`a evsla:MeasurementMethod`): `evsla:activeMeasurement`,
  `evsla:twamp`
- TimeWindow (`a evsla:TimeWindow`): `evsla:fiveMinuteWindow`,
  `evsla:oneHourWindow`, `evsla:monthlySlaWindow`
- ComparisonOperator (`quan` functions, comments define direction):
  `quan:smaller`, `quan:atLeast`, `quan:atMost`, `quan:greater`, `quan:inRange`

The ontology does **not** assert any metric→operator binding. Operator
*direction* is therefore not a retrievable fact; retrieval supplies the
operator terms and their direction-defining comments, and the LLM resolves
direction from the natural-language comparison wording (see 7.3).

Traversal explicitly **excludes** `rdf:type`, `rdfs:subClassOf`,
`rdfs:subPropertyOf`, `rdfs:domain`, `rdfs:range` as edges to walk (they remain
available as resource metadata in the index but are never serialized as a
fact dump).

## 5. Offline Resource Index

Ported from the Experiment 2 design (the part that was correct), into
`GraphRag/`.

Per-resource record `OntologyResource`:

- `uri` — full official IRI (authoritative, never lost)
- `curie` — canonical CURIE
- `labels`, `alt_labels` — `rdfs:label` / `skos:altLabel`
- `comment` — first `rdfs:comment`
- `role` — `class` | `property` | `instance`
- `rdf_types` — for instances, the class CURIEs (used to derive `role_class`)
- `role_class` — which closed role this value belongs to (Statistic / Scope /
  MeasurementMethod / TimeWindow / Metric / ComparisonOperator), or null

Persisted to `GraphRag/index/`:
`resources.json`, `resource_embeddings.npy`, `manifest.json` (with ontology
fingerprint + embedding model so staleness is detectable). Build is offline
and idempotent; a `--check` mode never calls an API.

## 6. Online Grounding (entry-point retrieval)

- **Lexical** (deterministic): exact `label` / `altLabel` / normalized
  CURIE-local-name match = 1.0; token-subset = 0.8; Jaccard overlap =
  `0.6 * IoU`. Exact-match priority is mandatory (it is the precision the old
  KGE grounder lacked).
- **Vector**: one query-embedding call; cosine vs resource-text embeddings;
  cutoff 0.20.
- Combined score `0.45*lexical + 0.55*vector`; return top-K entry resources.
- **No seed-selection LLM call.** Online cost per case = 1 embedding call +
  1 generation call.

## 7. Graph Core: traversal + role-scoped closed vocabulary

### 7.1 Connective-relation traversal

From the grounded entry resources, traverse the **whitelisted connective
object-properties only** (Section 4 table), one hop, in the schema sense:
reaching the connective hubs `evsla:SlaExpectation` and
`evsla:HubAndSpokeTopology` and enumerating the role edges they expose
(`hasMetric → Metric`, `hasThreshold → quan:Quantity`, `hasStatistic →
Statistic`, …). Plumbing predicates are never followed.

The output of this step is the set of **reached roles** plus the readable
`(Class) -[property]-> (RangeClass)` edges.

### 7.2 Role-scoped closed vocabulary (decision: query-specific, not full)

For **each reached role only**, attach that role's closed instance set from the
index (Section 4). Roles not reached by grounding are omitted — this keeps the
context query-specific and retrieval-like rather than a static dump.

A role is "reached" when grounding lands on a resource whose `role_class` is
that role, or on a connective hub that exposes the role edge. In practice an
SLA intent grounds a metric/threshold and thereby reaches the SlaExpectation
hub, which exposes the metric/threshold/statistic/scope/method/window roles;
which of those closed sets are attached is still gated by what the query
grounds to, so a latency-only single-spoke case does not pull the topology
spoke vocabulary it does not need.

### 7.3 ComparisonOperator role (operator is retrieval-supplied)

When grounding reaches a metric + threshold (i.e. a comparison condition is
implied), attach the ComparisonOperator closed set
(`quan:smaller`/`atLeast`/`atMost`/`greater`/`inRange`) **with their
`rdfs:comment` direction definitions**. Retrieval supplies the operator
*terms and their precise meaning*; the LLM picks the *direction* from the NL
wording ("below"/"less than" → smaller, "at least"/"no less than" → atLeast),
exactly as it reads the threshold value from NL. This is the correct division
of labor because the ontology does not bind metric→operator. Operator thereby
becomes a retrieval-tested dimension rather than a prompt-guaranteed one.

### 7.4 Bounds

Context size is bounded by ontology structure (the connective set and closed
vocabularies are small and fixed), not by a token target. A token guard caps
the assembled input as pathological-execution protection only: if the request
would exceed the model input envelope minus reserved output, drop
lowest-ranked complete items (never truncate a term, edge, or value) and record
the drop in the audit. Under normal operation the guard never fires; target
retrieval context is a few hundred tokens.

## 8. Context Serialization Format

Self-contained block injected into the user message:

```text
### Canonical prefixes
evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/>
icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/>
quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/>
met:, log:, rdf:, rdfs:, xsd: ...

### Grounded terms (NL concept -> ontology term)
- latency -> evsla:latency (a rdf:Property, subPropertyOf met:metric) -- network latency metric
- p95     -> evsla:p95     (a evsla:Statistic) -- 95th percentile

### Connective relations (how an SLA expectation wires together)
- evsla:SlaExpectation evsla:hasMetric            -> rdf:Property (metric)
- evsla:SlaExpectation evsla:hasThreshold         -> quan:Quantity
- evsla:SlaExpectation evsla:hasStatistic         -> evsla:Statistic
- evsla:SlaExpectation evsla:hasScope             -> evsla:Scope
- evsla:SlaExpectation evsla:hasMeasurementMethod -> evsla:MeasurementMethod
- evsla:SlaExpectation evsla:hasTimeWindow        -> evsla:TimeWindow
- evsla:HubAndSpokeTopology evsla:hasHub          -> evsla:HubSite
- evsla:HubAndSpokeTopology evsla:hasSpoke        -> evsla:SpokeSite

### Closed vocabulary per reached role (pick one per slot)
- Statistic: evsla:p95, evsla:p99, evsla:average, evsla:maximum, evsla:minimum
- Scope: evsla:hubToAllSpokes, evsla:perSpoke, evsla:specificSpoke
- ComparisonOperator: quan:smaller (a<b), quan:atLeast (a>=b), quan:atMost (a<=b), ...
```

Only reached roles appear under the closed-vocabulary section.

## 9. Structure-Only Prompt Profile

Add a third profile to `evsla_prompt.build_evsla_system_prompt`:
`strong` (existing) | `weak` (existing) | **`structure_only`** (new).

`structure_only` **keeps** (assembly architecture):

- the Turtle graph skeleton: intent → PropertyExpectation → Target →
  HubAndSpoke topology;
- target consistency rules;
- the `log:Condition` pattern *shape* (where an operator applies to the
  observed value and the shared threshold node), with the operator left as a
  slot: "choose the comparison operator from the supplied operator vocabulary
  based on the NL comparison wording";
- output/format constraints (pure Turtle, no markdown/JSON).

`structure_only` **withholds** (supplied by retrieval):

- all official `@prefix` declarations;
- metric / statistic / scope / measurement-method / time-window term mappings;
- operator terms and metric→operator bindings;
- the closed vocabularies.

### 9.1 Lines under the structure-only profile

- **GraphRAG-structure**: structure_only prompt + redesigned retrieval.
- **KGE-structure**: structure_only prompt + existing KGE retrieval.
- **LLM-only-structure**: structure_only prompt, no retrieval (control floor).
- **strong** lines remain as the quality upper-bound reference.

### 9.2 Few-shot must not leak the withheld vocabulary

The existing `few_shot_samples.json` contains full Turtle with real `evsla:`
terms and `@prefix` declarations. Using it under `structure_only` would leak
exactly the vocabulary the profile withholds and defeat the experiment.
Therefore the structure-only lines use a **sanitized skeleton few-shot**
(`few_shot_structure_only.json`, new artifact): the same Turtle assembly shape
as the real examples but with placeholder ontology terms (e.g.
`ex:metricTerm`, `ex:statisticTerm`) and no `@prefix`/EVSLA CURIEs. All three
structure-only lines (GraphRAG-structure, KGE-structure, LLM-only-structure)
share this identical skeleton few-shot, and the retrieval context occupies the
same user-message location for both retrieval lines. The `strong` upper-bound
line continues to use the existing vocabulary-rich `few_shot_samples.json`.

## 10. Test Case Expansion

Author 20 new cases `TC021`–`TC040` in a **new file `test_cases_40.json`**
(the existing `test_cases_20.json` is left unchanged). `test_cases_40.json`
contains all 40 cases (TC001–TC040) so the existing 20 remain available as a
regression set and the new experiment runs over the full 40.

Each new case uses the existing self-gold schema (`id`, `category`,
`complexity`, `tenant`, `scope.hub`, `scope.spokes`, `performance_metrics[...]`
with metric/operator/threshold/statistic/scope/measurement_method/time_window/
ontology_term, `topology`, `nl_intent`, `expected_tio_elements`,
`ontology_terms`, `expected_json_nodes`). Every case must be representable by
the frozen EVSLA ontology, must not require `evsla:jitter` or any invented
term, and each gold spec is manually reviewed.

Current 20 cases are monotonous: all single-metric, only `hubToAllSpokes`
(14) / `specificSpoke` (6), **zero `perSpoke`**, only one multi-metric case,
no per-spoke-differentiated conditions, max 4 spokes. The 20 new cases close
these gaps across four dimensions (≈5 each, overlap allowed):

1. **perSpoke scope** — the only untested scope term; exercises Scope closed
   vocab + `hasScope` wiring.
2. **Per-spoke differentiated metric/threshold** — different spokes carry
   different thresholds or metrics in one intent; exercises `applies_to_spokes`
   pairing and `hasScope`/`hasSpoke` wiring.
3. **Multi-metric single topology** — latency + packetLoss + bandwidth in one
   intent; exercises multiple coexisting expectations on a shared topology.
4. **Large fan-out + rarely-used vocabulary** — 5–6 spokes; opportunistically
   covers `average`/`maximum`/`minimum` statistics and `oneHourWindow`/
   `monthlySlaWindow`.

## 11. Evaluation and Success Criteria

Reuse the existing `semantic_eval.py` (11-dimension graph-binding evaluator);
do not build a new evaluator. Run the full 40 cases.

Core comparisons:

```text
retrieval_information_gain = GraphRAG-structure - LLM-only-structure   (> 0 proves retrieval recovers knowledge)
replacement_gap            = GraphRAG-structure - strong               (closer to 0 is better)
graphrag_vs_kge            = GraphRAG-structure - KGE-structure
```

Report side by side, separately (no single CP score): composite + per-dimension
(topology, scope, operator especially) + tokens/case. Token cost is a
first-class outcome.

Success is defined as:

- **GraphRAG-structure clearly beats the LLM-only-structure floor** (positive
  information gain), and
- **retrieval token cost is far below the old ~13.5k/case** (target: a few
  hundred to low-single-thousand per case), and
- operator and scope dimensions are materially recovered relative to the floor.

A secondary, stronger outcome is GraphRAG-structure approaching the strong
upper bound.

## 12. Module and File Layout (in `TIO_Experiment/GraphRag/`)

- `resource_index.py` (new) — `OntologyResource` + index build from the merged
  ontology graph, including `role_class` derivation.
- `build_index.py` (new) — offline index build to `GraphRag/index/` with
  fingerprint + `--check`.
- `subgraph_retriever.py` (rewrite) — grounding (lexical-exact + vector) +
  connective-relation traversal + role-scoped closed-vocab assembly.
- `context_builder.py` (new) — serialization (@prefix + grounded + relations +
  reached-role closed vocab) + token guard + retrieval audit.
- `nl_to_tio.py` (modify) — remove the seed-selection LLM call, wire the new
  pipeline, add `--prompt-profile {strong,weak,structure_only}`.
- `evsla_prompt.py` (modify) — add the `structure_only` profile.
- `test_cases_40.json` (new) — 40 cases (TC001–TC040).
- `few_shot_structure_only.json` (new) — sanitized skeleton few-shot with
  placeholder ontology terms and no EVSLA vocabulary, shared by all
  structure-only lines (see 9.2).

Existing fixed output/scoring paths (`tio_outputs/`, `phase1/`) are reused per
the repo convention; structure-only runs write to clearly-suffixed
experiment keys so they do not overwrite the strong-prompt baselines.

## 13. Testing

Offline gate (no API tokens):

- grounding precision: exact-label queries resolve to the correct URI;
- traversal hygiene: only whitelisted connective properties are followed;
  no `rdf:type`/`subClassOf`/`domain`/`range` edges appear in output;
- context self-containment: `@prefix` block present; every emitted CURIE's
  namespace is declared; only reached roles' closed vocab is present;
- token budget: assembled retrieval context within target; guard drops
  lowest-ranked items without truncation when forced.

Evaluator fixtures (confirm `semantic_eval` discriminates): a `perSpoke` case,
a missing-spoke case, and a metric-to-wrong-spoke mispairing case each produce
the expected dimension penalties.

Gold validation: all 40 cases representable by the frozen ontology; no
`evsla:jitter`; no invented terms.

Do not spend API tokens before the offline gate and evaluator fixtures pass.

## 14. Scope and Non-Goals

- KGE is **not** redesigned; it is reused as the comparison retrieval line.
- KAG is out of scope.
- No new evaluator; reuse `semantic_eval.py`.
- Output target is Turtle (this repo's pipeline), not JSON-LD.
- No Microsoft-GraphRAG indexing (chunking / extraction / communities).
- The six-cell Experiment 2 harness is **not** ported; only the
  structure-only profile needed to measure the redesign is added.

## 15. Captured Nuances

- Operator direction is LLM-inferred from NL, not retrieved (ontology lacks the
  binding). This is intentional, not a gap.
- Closed vocab is role-scoped (only reached roles), chosen over full-listing to
  stay query-specific even though full-listing would maximize raw validity.
- The connective traversal will surface a similar core wiring per SLA case
  because the domain is narrow; this is acceptable — it is the domain's real
  relational structure, and role-scoping still varies the closed-vocab payload
  per query.
