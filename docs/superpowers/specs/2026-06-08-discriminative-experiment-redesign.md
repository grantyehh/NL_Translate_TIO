# Discriminative Experiment Redesign

Date: 2026-06-08

## 1. Objective

The experiment will no longer ask only whether GraphRAG or KGE has a higher
average coverage score than LLM-only.

The primary research question is:

> Can GraphRAG or KGE replace ontology knowledge that is currently duplicated
> in the system prompt and few-shot examples, while preserving enough quality
> to justify retrieval tokens, latency, and preparation cost?

The experiment must distinguish:

- improvements caused by the shared system prompt or few-shot examples;
- improvements caused by ontology retrieval, grounding, or reasoning;
- cases where all methods reach a ceiling;
- cases where retrieval adds cost without useful quality improvement.

## 2. Hypotheses

The pilot evaluates the following hypotheses:

- H1: A full system prompt plus EVSLA few-shot examples is a strong baseline for
  the current fixed EVSLA task.
- H2: A structural prompt plus placeholder-style few-shot examples and retrieval
  can preserve the baseline quality without duplicating EVSLA mappings in the
  prompt.
- H3: Retrieval without structural few-shot guidance is less stable than the
  hybrid-lite configuration.
- H4: GraphRAG or KGE is worthwhile only if it preserves or improves semantic
  quality and ontology validity at an acceptable additional cost.
- H5: Complex linguistic composition does not necessarily benefit from graph
  retrieval unless the method also improves decomposition or reasoning.
- H6: A method is operationally worthwhile only when its quality or reliability
  gain compensates for online tokens, latency, and amortized preparation cost.

## 3. Two-Stage Design

### Stage 1: Exploratory Configuration Comparison

Run the following three technical lines:

- 30 test cases;
- 10 EVSLA-grounding cases;
- 10 linguistic-complexity cases;
- 10 EVSLA-structure cases;
- 3 independent runs per configuration and case;
- technical lines: LLM-only, GraphRAG, and KGE.

The main configurations are:

- Full Prompt baseline: LLM-only with the complete structural prompt, EVSLA
  mappings, and EVSLA few-shot examples.
- Hybrid-lite GraphRAG and Hybrid-lite KGE: structural prompt, placeholder-style
  few-shot example, no hard-coded EVSLA mapping, and method-specific retrieval.
- Retrieval-only GraphRAG and Retrieval-only KGE: minimal output contract, no
  EVSLA mapping, no structural few-shot example, and method-specific retrieval.

This produces five main experimental cells and 450 generation runs.

Add one diagnostic control:

- Structure-only LLM: the same structural prompt and placeholder-style few-shot
  example used by Hybrid-lite, but without retrieval.

This control adds 90 runs, for 540 total Stage 1 generation runs. It is not a
fourth technical line. It measures the quality lost when EVSLA mappings are
removed and therefore makes the retrieval contribution identifiable.

Stage 1 identifies whether retrieval can replace prompt-embedded ontology
knowledge and which case patterns expose quality or stability differences. All
results remain in the report, including ties.

### Stage 2: Confirmatory Prompt Ablation

Build a preregistered confirmation set before inspecting its outputs:

- retain a fixed representative sample from every suite;
- include newly authored cases that match the discriminative patterns observed
  in Stage 1;
- do not reuse individual Stage 1 cases as confirmation evidence;
- freeze the confirmation cases, scoring rules, thresholds, prompts, model, and
  randomization procedure before running them.

Run the frozen confirmation set with the same configurations and repeat every
cell three times.

This separates exploratory findings from confirmatory evidence and prevents
selection of only cases favorable to a particular method.

## 4. Test Suites

### 4.1 EVSLA Grounding

These cases require ontology knowledge not explicitly supplied by the minimal
or structural prompt. All cases remain in the Enterprise VPN hub-and-spoke
domain and use the project-specific EVSLA ontology.

Coverage should include:

- aliases and paraphrases that do not repeat ontology labels;
- similar metrics or relations that are easy to confuse;
- class-versus-property distinctions;
- domain and range constraints;
- scope, statistic, measurement method, and time-window combinations;
- contextually plausible networking background terms that are unrelated to the
  requested SLA and therefore must not produce additional expectations or
  ontology facts.

The suite should not be solvable by copying one fixed mapping table.

Background terms such as MPLS, BGP, or OSPF are not treated as incorrect user
instructions. They test whether the pipeline can separate relevant SLA
requirements from incidental context. Cases where the user explicitly assigns
an incompatible ontology term are instead classified as invalid or
contradictory intents; their expected behavior is to report the conflict, not
silently correct or follow it.

### 4.2 Linguistic and Semantic Complexity

These cases stress interpretation and composition rather than missing ontology
vocabulary.

Coverage should include:

- two to four SLA metrics in one intent;
- different scopes or sites for different metrics;
- exceptions and conditional clauses;
- negation and contrast;
- cross-sentence references;
- omitted values that must remain unspecified rather than invented;
- conflicting or infeasible requirements that should be flagged;
- Chinese and English terminology mixed in natural ways.

The expected output must state when the source intent is ambiguous or invalid.
Silently inventing a value is an error.

### 4.3 EVSLA Ontology Structure

These cases test relationships in the existing project-defined EVSLA ontology
that cannot be recovered reliably from a short metric mapping table alone.

The experiment does not claim that the model was certainly never exposed to
EVSLA during training, because model training data cannot be inspected. It uses
the following reproducible operational assumption instead:

- EVSLA was created for this project and is not treated as public base-TIO
  knowledge;
- Hybrid-lite, Retrieval-only, and Structure-only prompts contain no concrete
  EVSLA CURIE mapping table;
- LLM-only receives no EVSLA TTL or retrieval context;
- GraphRAG and KGE receive the same frozen EVSLA TTL through their respective
  knowledge mechanisms.

The ten cases should require grounding natural business language to existing
EVSLA elements covering:

- EVSLA intent, service, tenant, topology, hub, spoke, and expectation classes;
- latency, packet-loss, and guaranteed-bandwidth metrics;
- p95, p99, and minimum statistics;
- all-spoke and specific-spoke scopes;
- TWAMP and active-measurement methods;
- threshold, metric, statistic, scope, measurement-method, and time-window
  relations.

Natural-language inputs must not expose `evsla:*` CURIEs. Correct answers must
depend on terms or relations found in the frozen EVSLA TTL. All
knowledge-enhanced methods must complete their required indexing or training
from that same ontology version before the run.

## 5. Knowledge Configurations

All configurations use the same generation model, decoding parameters, base
output contract, and test cases.

### 5.1 Full Prompt Baseline

Uses LLM-only with:

- the complete JSON-LD contract and assembly rules;
- the current EVSLA mappings;
- the current EVSLA few-shot examples;
- no retrieval.

This represents the current prompt-engineering solution.

### 5.2 Hybrid-Lite

Uses GraphRAG or KGE with:

- the JSON-LD contract and structural assembly rules;
- one placeholder-style few-shot example;
- no concrete metric, statistic, scope, method, class, or relation mappings;
- retrieved EVSLA ontology context.

The placeholder example may use tokens such as `<METRIC_CURIE>` and
`<STATISTIC_CURIE>`, but must not disclose the concrete EVSLA answer space.

### 5.3 Retrieval-Only

Uses GraphRAG or KGE with:

- a minimal JSON-LD output contract;
- no EVSLA mapping;
- no structural few-shot example;
- retrieved EVSLA ontology context.

This is an ablation that tests whether retrieval can teach both ontology
grounding and output assembly without prompt examples.

### 5.4 Structure-Only LLM Control

Uses the exact Hybrid-lite structural prompt and placeholder example without
retrieval. Its purpose is to isolate the information contributed by retrieval.

All prompt texts and retrieval configurations must be versioned and hashed in
each run manifest.

## 6. Discriminative Case-Type Rule

A case type is considered discriminative in Stage 1 when at least one
configuration shows a practically meaningful difference from its relevant
control.

Primary threshold:

- at least 10 percentage points in the preregistered semantic-quality score
  between Hybrid-lite and Structure-only LLM, or between Hybrid-lite and Full
  Prompt;
- the direction is reproduced in at least two of the three runs;
- the difference is not caused solely by JSON parsing or formatting failure.

Secondary discrimination signals:

- lower critical-error rate;
- higher exact semantic-match rate;
- lower hallucination rate;
- higher run-to-run consistency;
- a clear quality-versus-cost trade-off even when the quality difference is
  smaller than 10 percentage points.

The unit selected for further study is a documented case pattern or error
category, not an individual favorable test case.

## 7. Evaluator Redesign

The current evaluator remains as a compatibility and surface-contract layer,
but it is not sufficient as the primary quality measure.

### 7.1 Deterministic Contract Validation

Validate:

- valid JSON and JSON-LD structure;
- required fields and types;
- identifier consistency;
- one expectation per intended metric where required;
- no unsupported Markdown or prose wrapper.

### 7.2 Source-Faithfulness Scoring

Compare output fields against a structured gold specification:

- tenant, hub, spokes, and referenced service;
- metric, operator, threshold value, and unit;
- statistic, scope, measurement method, and time window;
- condition, exception, and metric-to-site association;
- number of requirements expressed in the source.

Score false positives as well as omissions. An extra invented metric, site,
threshold, or constraint is a semantic error.

### 7.3 Ontology Validity

Parse the active TTL graph and validate:

- every emitted ontology CURIE resolves;
- emitted classes and properties have the correct role;
- domain and range constraints are respected;
- deprecated terms are rejected or penalized;
- private EVSLA terms are accepted only when present in the active ontology;
- unsupported or hallucinated predicates and types are reported.

SHACL should be used when suitable shapes exist. Additional graph checks may
cover constraints not represented by SHACL.

### 7.4 Completeness and Minimality

Replace raw node-count targets as the main verbosity measure with:

- required facts present;
- redundant duplicate expectations;
- unrelated ontology terms;
- unsupported default values;
- semantic facts per JSON node or per output token.

Node count remains a diagnostic metric, not a quality proxy.

### 7.5 Ambiguity and Invalid-Intent Handling

Some cases will have a gold status such as:

- valid and fully specified;
- valid but underspecified;
- ambiguous;
- internally conflicting;
- unsupported by the active ontology.

The evaluator checks whether the pipeline preserves uncertainty or reports the
problem instead of fabricating a normal intent.

### 7.6 Human Review

Use blinded human review for cases where deterministic checks cannot fully
resolve semantic equivalence.

Reviewers see randomized outputs without pipeline labels. A rubric scores
faithfulness, completeness, ontology correctness, and harmful invention.
Disagreements are recorded and adjudicated.

## 8. Metrics

Report metrics by technical line, knowledge configuration, suite, and run:

- parse and contract success rate;
- exact semantic-match rate;
- field-level precision, recall, and F1;
- ontology-validity rate;
- critical-error rate;
- hallucinated-fact rate;
- ambiguity/conflict handling accuracy;
- run-to-run consistency;
- input, output, and total online tokens;
- online call count;
- end-to-end latency;
- one-time preparation tokens and time;
- amortized cost at declared workload sizes.

Do not collapse the primary conclusion into a single unweighted average.

## 9. Utility Decision

Quality is primary. Cost decides whether a quality gain is operationally worth
using.

For each method and experimental cell, report against both relevant controls:

```text
replacement_quality_delta = hybrid_lite_quality - full_prompt_quality
retrieval_information_gain = hybrid_lite_quality - structure_only_quality
token_multiplier = method_online_tokens / full_prompt_online_tokens
latency_multiplier = method_latency / full_prompt_latency
amortized_cost_delta(N) = method_cost(N) - full_prompt_cost(N)
```

A method is classified as:

- **worthwhile** when it produces a meaningful quality or critical-error
  improvement at an acceptable declared cost;
- **quality-positive but inefficient** when it improves quality but has an
  excessive cost multiplier;
- **cost-neutral alternative** when quality is equivalent and operational cost
  is comparable;
- **not worthwhile** when it adds cost without meaningful quality or reliability
  improvement.

The report must show the raw dimensions behind the classification. It must not
hide value judgments inside an unexplained weighted score.

## 10. Statistical Treatment

Three runs measure generation stability but are not enough for strong
population-level significance claims.

The pilot will therefore report:

- mean and standard deviation across runs;
- paired per-case differences against Full Prompt and Structure-only LLM;
- bootstrap confidence intervals across test cases;
- exact counts of wins, ties, and losses;
- effect sizes and critical-error differences.

Stage 1 findings are exploratory. Only the frozen Stage 2 set is used for
confirmatory claims.

## 11. Reproducibility and Controls

Each run manifest records:

- git commit and dirty-worktree status;
- model and API;
- knowledge configuration, prompt version, and prompt hash;
- few-shot file hash;
- test-suite version and hash;
- base TIO and EVSLA ontology hashes;
- retrieval/index/training artifact version;
- temperature and other decoding parameters;
- start time, end time, latency, token usage, and errors;
- random run order.

All configurations must use the same model and base output contract.
Method-specific retrieval context is allowed only in GraphRAG and KGE cells.
Post-generation repair that changes semantics must be disabled or scored as
part of that method rather than silently normalized.

## 12. Deliverables

The redesign will produce:

- versioned Stage 1 and Stage 2 test suites;
- four versioned knowledge configurations, including the Structure-only
  diagnostic control;
- structured gold specifications;
- a frozen, versioned copy of the existing EVSLA ontology used by all
  knowledge-enhanced pipelines;
- a strict evaluator and human-review rubric;
- run manifests and raw per-run reports;
- quality, stability, token, latency, and amortized-cost comparisons;
- an error taxonomy by suite and pipeline;
- a final conclusion describing where each method is worthwhile.

## 13. Success Criteria

The redesign succeeds when it can support defensible statements such as:

- Full Prompt is sufficient for familiar one-metric cases;
- Hybrid-lite GraphRAG preserves Full Prompt quality while replacing
  prompt-embedded EVSLA mappings at a stated token and latency multiplier;
- Structure-only LLM loses ontology accuracy that Hybrid-lite recovers, showing
  that the gain comes from retrieved information rather than prompt structure;
- Retrieval-only is less stable than Hybrid-lite, showing that structural
  guidance remains necessary;
- KGE reduces URI or relation errors for a specific knowledge-gap pattern;
- LLM-only is the preferred default for specified regions of the task space;
- a knowledge-enhanced method should be invoked only for identified regions
  where its measured utility is positive.

The experiment is still successful if no enhanced method is worthwhile. A
well-supported negative result is preferable to a ceiling-effect comparison
that cannot distinguish the methods.
