# Prompt Knowledge vs Retrieval Experiment

Date: 2026-06-08

## 1. Research Question

The existing experiment gives LLM-only, GraphRAG, and KGE the same full system
prompt and EVSLA few-shot examples. Retrieval methods additionally receive
ontology context. The results show little quality improvement from retrieval
while GraphRAG and KGE consume additional resources.

The new experiment asks:

> Can EVSLA ontology knowledge be removed from the system prompt and few-shot
> examples and supplied by GraphRAG or KGE retrieval instead, without losing
> output quality, and is the result worth the additional token and latency cost?

## 2. Technical Lines

Only these technical lines are evaluated:

- LLM-only
- GraphRAG
- KGE

All lines use the same generation model, decoding parameters, base JSON-LD
contract, test cases, and frozen EVSLA ontology version.

## 3. Knowledge Configurations

### 3.1 Full Prompt Baseline

LLM-only receives:

- the complete JSON-LD structure and assembly rules;
- concrete EVSLA classes, properties, CURIEs, and mapping rules;
- the current EVSLA few-shot examples;
- no retrieval.

This represents the current prompt-engineering solution.

### 3.2 Hybrid-Lite

GraphRAG and KGE each receive:

- the JSON-LD structure and assembly rules;
- one placeholder-style structural example;
- no concrete EVSLA ontology mappings in the prompt;
- EVSLA knowledge supplied by their retrieval method.

The structural example may use placeholders such as `<METRIC_CURIE>`,
`<STATISTIC_CURIE>`, and `<SCOPE_CURIE>`. It must not disclose the actual EVSLA
mapping.

This is the primary retrieval configuration.

### 3.3 Retrieval-Only

GraphRAG and KGE each receive:

- the minimal JSON-LD output contract;
- no concrete EVSLA mapping;
- no few-shot example;
- EVSLA knowledge supplied by their retrieval method.

This tests whether retrieval can provide both ontology grounding and enough
information for output assembly.

### 3.4 Structure-Only LLM Control

LLM-only receives the exact structural prompt and placeholder example used by
Hybrid-lite, but no retrieval.

This control is necessary to measure whether Hybrid-lite recovers ontology
knowledge through retrieval rather than succeeding from the structural prompt
alone.

## 4. Experimental Cells

| Cell | Technical line | Prompt knowledge | Retrieval |
|---|---|---|---|
| Full Prompt | LLM-only | Full structure, EVSLA mapping, EVSLA few-shot | None |
| Structure-only | LLM-only | Structure and placeholder example | None |
| Hybrid-lite GraphRAG | GraphRAG | Structure and placeholder example | GraphRAG |
| Hybrid-lite KGE | KGE | Structure and placeholder example | KGE |
| Retrieval-only GraphRAG | GraphRAG | Minimal contract | GraphRAG |
| Retrieval-only KGE | KGE | Minimal contract | KGE |

The primary comparison is:

```text
Full Prompt LLM-only
vs
Hybrid-lite GraphRAG
vs
Hybrid-lite KGE
```

The Structure-only and Retrieval-only cells are diagnostic controls.

## 5. Test Cases

Use 30 new Enterprise VPN hub-and-spoke cases. Every case uses the existing
project-defined EVSLA ontology.

The case semantics follow the planning deck
`20260427_企業VPN_SLA管理監測規劃_v1 (1).pptx`:

```text
tenant
+ hub/spoke range
+ performance metric
+ threshold
+ statistic
+ measurement method
+ monitoring time window
```

The deck mentions jitter as a possible measured metric, but the current EVSLA
TTL does not define a jitter metric. Jitter is excluded from the 30 generation
cases unless the ontology is explicitly extended before the experiment. The
evaluator must still reject an invented `evsla:jitter` term.

### 5.1 EVSLA Grounding: 10 Cases

Test whether natural language is grounded to the correct EVSLA terms:

- metric synonyms and paraphrases;
- statistic, scope, measurement method, and time-window mappings;
- similar classes and properties;
- expressions that do not reveal `evsla:*` CURIEs.

### 5.2 Semantic Composition: 10 Cases

Test whether multiple requirements are assembled correctly:

- two to four metrics in one intent;
- different metrics applied to different spokes;
- per-spoke versus all-spoke wording;
- omitted measurement or time-window fields that must not be invented.

### 5.3 EVSLA Structure: 10 Cases

Test ontology relationships that are not represented by a short metric mapping:

- intent, service, tenant, topology, hub, spoke, and expectation classes;
- class-versus-property usage;
- domain and range constraints;
- correct relationships among metric, threshold, statistic, scope,
  measurement method, and time window;
- plausible but irrelevant networking terms that must not create extra facts.

Each case must include a manually reviewed structured gold specification.

### 5.4 Gold Specification

Each case uses this evaluator-oriented shape:

```json
{
  "id": "TC101",
  "tenant": {
    "name": "企業A",
    "ontology_type": "evsla:Tenant"
  },
  "service": {
    "ontology_type": "evsla:EnterpriseVpnService"
  },
  "topology": {
    "ontology_type": "evsla:HubAndSpokeTopology",
    "hub": {"name": "台北總部", "ontology_type": "evsla:HubSite"},
    "spokes": [
      {"name": "台中分點", "ontology_type": "evsla:SpokeSite"}
    ]
  },
  "requirements": [
    {
      "metric": "evsla:latency",
      "operator": "LESS_THAN",
      "threshold": {"value": 50, "unit": "ms"},
      "statistic": "evsla:p95",
      "scope": "evsla:hubToAllSpokes",
      "applies_to_spokes": ["台中分點"],
      "measurement_method": "evsla:twamp",
      "time_window": "evsla:fiveMinuteWindow"
    }
  ],
  "must_not_emit": ["evsla:jitter"],
  "allowed_defaults": []
}
```

All 30 cases must be representable by the frozen EVSLA ontology. If the source
text omits a field, the generator must not add it unless the value is explicitly
listed in `allowed_defaults`.

## 6. Runs

Run every experimental cell three times per test case.

```text
6 cells x 30 cases x 3 runs = 540 generation runs
```

If cost must be reduced, run one pass first and perform the remaining two runs
only after the evaluator and run pipeline are verified.

## 7. Evaluator

The evaluator must score more than term presence.

### 7.1 Contract

- valid JSON and required JSON-LD structure;
- required fields and valid field types;
- correct number and type of expectations.

### 7.2 Semantic Faithfulness

Compare the output with the structured gold specification:

- tenant, hub, spokes, and service;
- metric, operator, threshold value, and unit;
- statistic, scope, measurement method, and time window;
- metric-to-site associations;
- missing requirements;
- invented metrics, sites, values, or constraints.

Canonicalize every generated expectation into a requirement tuple:

```text
(metric, operator, value, unit, statistic, scope,
 applies_to_spokes, measurement_method, time_window)
```

Match generated and gold requirements by minimum field-error cost rather than
array position. This prevents reordered expectations from being penalized and
detects incorrect metric-to-site pairing.

### 7.3 Ontology Validity

Validate against the frozen TIO and EVSLA TTL files:

- every emitted CURIE exists;
- classes and properties are used in the correct role;
- domain and range constraints are respected;
- topology uses `evsla:hasHub` with `evsla:HubSite` and `evsla:hasSpoke` with
  `evsla:SpokeSite`;
- SLA fields use valid instances of `evsla:Statistic`, `evsla:Scope`,
  `evsla:MeasurementMethod`, and `evsla:TimeWindow`;
- unsupported predicates and types are reported.

### 7.4 Minimality

Report:

- duplicate expectations;
- unrelated ontology terms;
- invented defaults;
- JSON node and output-token counts.

### 7.5 Scoring

Produce separate dimensions instead of only one aggregate score:

```text
contract_score
entity_topology_f1
requirement_field_f1
requirement_exact_match
ontology_validity
hallucination_rate
case_exact_match
```

Definitions:

- `entity_topology_f1`: precision/recall/F1 over tenant, hub, spokes, service,
  topology, and their ontology types;
- `requirement_field_f1`: micro F1 over the nine fields in each canonical
  requirement tuple;
- `requirement_exact_match`: percentage of gold requirements whose full tuple
  is matched;
- `ontology_validity`: valid emitted ontology assertions divided by all emitted
  ontology assertions;
- `hallucination_rate`: unsupported or source-absent semantic facts divided by
  all emitted semantic facts;
- `case_exact_match`: true only when contract, entities, topology, all
  requirements, and ontology validity are correct with no hallucinated facts.

The primary quality metric is macro-averaged `requirement_field_f1`, reported
together with `case_exact_match` and `hallucination_rate`. Contract or ontology
failures must remain visible and must not be hidden by a weighted average.

### 7.6 Evaluator Verification

Before evaluating generated outputs, create fixtures for:

- fully correct output;
- wrong tenant, hub, or spoke;
- missing spoke;
- wrong threshold value or unit;
- wrong statistic, scope, method, or time window;
- metric assigned to the wrong spoke;
- missing and duplicate requirements;
- invented metric or default;
- unknown CURIE;
- class/property misuse;
- domain/range violation;
- fabricated `evsla:jitter` or another unknown EVSLA term.

Each fixture has fixed expected scores and error codes. Deterministic contract,
semantic, and ontology checks must pass these tests before API experiments are
run.

## 8. Metrics

Report results per cell and test-case category:

- parse and contract success rate;
- exact semantic-match rate;
- field-level precision, recall, and F1;
- ontology-validity rate;
- hallucinated-fact rate;
- run-to-run consistency;
- average online tokens;
- average API call count;
- end-to-end latency;
- preparation cost for GraphRAG and KGE.

### 8.1 Token Accounting

Record one row per API call with:

```text
run_id
configuration
technical_line
case_id
repeat
ledger
stage
model
api
input_tokens
output_tokens
total_tokens
```

Use these ledgers:

- `prep`: reusable ontology indexing, entity embeddings, and KGE training
  embeddings;
- `online`: all per-case retrieval and generation calls.

Use these online stages:

- LLM-only: `jsonld_generation`;
- GraphRAG: `seed_selection`, `grounding_embedding`,
  `jsonld_generation`;
- KGE: `retrieval_embedding`, `jsonld_generation`.

Report per case:

```text
generation_tokens
retrieval_tokens
online_total_tokens
api_call_count
```

Report preparation tokens separately and amortize them at 30, 100, and 1000
cases. Never combine prep and online tokens without labeling the workload size.

### 8.2 Latency Accounting

Measure elapsed time with `time.perf_counter_ns()` and store milliseconds.
Record both stage-level and case-level timing:

```text
prep_ontology_load_ms
prep_index_build_ms
prep_kge_training_ms
prompt_build_ms
retrieval_seed_ms
retrieval_embedding_ms
retrieval_graph_or_kge_ms
generation_api_ms
postprocess_ms
case_end_to_end_ms
```

Rules:

- `case_end_to_end_ms` starts immediately before per-case retrieval or prompt
  construction and ends after the output file is written;
- Full Prompt and Structure-only still record prompt construction,
  generation, post-processing, and end-to-end time;
- GraphRAG records seed-selection API, embedding API, local BFS, and context
  serialization separately;
- KGE records query embedding, local ranking/neighborhood/link prediction, and
  context formatting separately;
- ontology loading, index building, and KGE training are preparation costs, not
  per-case online latency;
- failed calls retain their elapsed time and error status;
- run order is randomized or rotated so one configuration is not always
  penalized by transient API conditions.

Report median and p95 latency in addition to mean because API latency is
typically skewed.

### 8.3 Cost Comparison

For each configuration report:

```text
avg_online_tokens_per_case
amortized_tokens_per_case_at_N
median_end_to_end_ms
p95_end_to_end_ms
quality_per_1k_online_tokens
```

`quality_per_1k_online_tokens` is diagnostic only:

```text
1000 * requirement_field_f1 / avg_online_tokens_per_case
```

The final decision must still show quality and cost separately.

## 9. Decision Rules

Use these comparisons:

```text
replacement_quality_delta =
    hybrid_lite_quality - full_prompt_quality

retrieval_information_gain =
    hybrid_lite_quality - structure_only_quality

token_multiplier =
    hybrid_lite_tokens / full_prompt_tokens

latency_multiplier =
    hybrid_lite_latency / full_prompt_latency
```

Interpretation:

- Hybrid-lite is useful if it approaches or exceeds Full Prompt quality and
  clearly improves over Structure-only LLM.
- Retrieval-only shows whether few-shot and structural guidance can be removed
  entirely.
- Retrieval is not worthwhile if it adds substantial token or latency cost
  without meaningful quality or reliability improvement.
- Full Prompt remains the preferred solution if it is equally accurate, more
  stable, and cheaper.

## 10. Expected Conclusion

The experiment should support one of these conclusions:

- Full system prompt and few-shot examples are sufficient for the current EVSLA
  NL-to-TIO task.
- Hybrid-lite GraphRAG or KGE can replace hard-coded ontology knowledge while
  preserving quality at an acceptable cost.
- Retrieval is useful only for specific EVSLA case categories.
- Retrieval-only is insufficient, so structural prompt guidance and at least
  one example remain necessary.
