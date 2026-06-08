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
- conditions, exceptions, and exclusions;
- missing or conflicting information that must not be invented.

### 5.3 EVSLA Structure: 10 Cases

Test ontology relationships that are not represented by a short metric mapping:

- intent, service, tenant, topology, hub, spoke, and expectation classes;
- class-versus-property usage;
- domain and range constraints;
- correct relationships among metric, threshold, statistic, scope,
  measurement method, and time window;
- plausible but irrelevant networking terms that must not create extra facts.

Each case must include a manually reviewed structured gold specification.

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
- metric-to-site and condition associations;
- missing requirements;
- invented metrics, sites, values, or constraints.

### 7.3 Ontology Validity

Validate against the frozen TIO and EVSLA TTL files:

- every emitted CURIE exists;
- classes and properties are used in the correct role;
- domain and range constraints are respected;
- unsupported predicates and types are reported.

### 7.4 Minimality

Report:

- duplicate expectations;
- unrelated ontology terms;
- invented defaults;
- JSON node and output-token counts.

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
