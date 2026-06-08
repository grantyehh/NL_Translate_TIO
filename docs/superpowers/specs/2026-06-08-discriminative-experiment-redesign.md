# Discriminative Experiment Redesign

Date: 2026-06-08

## 1. Objective

The experiment will no longer ask only whether GraphRAG, KGE, or KAG has a
higher average coverage score than LLM-only.

The primary research question is:

> Under which test-case types and prompt information levels does a
> knowledge-enhanced pipeline provide enough quality or reliability improvement
> to justify its additional token, latency, and preparation cost?

The experiment must distinguish:

- improvements caused by the shared system prompt or few-shot examples;
- improvements caused by ontology retrieval, grounding, or reasoning;
- cases where all methods reach a ceiling;
- cases where retrieval adds cost without useful quality improvement.

## 2. Hypotheses

The pilot evaluates the following hypotheses:

- H1: With a minimal schema prompt, knowledge-enhanced methods outperform
  LLM-only on cases requiring ontology knowledge that is absent from the prompt.
- H2: Adding ontology mappings to the prompt reduces the marginal benefit of
  retrieval.
- H3: A complete prompt plus representative few-shot examples causes a ceiling
  effect on familiar slot-filling cases.
- H4: Ontology-change cases produce the clearest benefit for methods that read
  the current ontology at inference or preparation time.
- H5: Complex linguistic composition does not necessarily benefit from graph
  retrieval unless the method also improves decomposition or reasoning.
- H6: A method is operationally worthwhile only when its quality or reliability
  gain compensates for online tokens, latency, and amortized preparation cost.

## 3. Two-Stage Design

### Stage 1: Exploratory Discrimination Pilot

Run all four pipelines using only the minimal prompt:

- 30 test cases;
- 10 knowledge-gap cases;
- 10 linguistic-complexity cases;
- 10 ontology-change cases;
- 3 independent runs per pipeline and case;
- 4 pipelines: LLM-only, GraphRAG, KGE, and KAG.

This stage requires 360 generation runs.

Stage 1 identifies discriminative case types and recurring error modes. All
results remain in the report, including cases where every method ties.

### Stage 2: Confirmatory Prompt Ablation

Build a preregistered confirmation set before inspecting its outputs:

- retain a fixed representative sample from every suite;
- include newly authored cases that match the discriminative patterns observed
  in Stage 1;
- do not reuse individual Stage 1 cases as confirmation evidence;
- freeze the confirmation cases, scoring rules, thresholds, prompts, model, and
  randomization procedure before running them.

Run the confirmation set at all three prompt information levels and repeat every
cell three times.

This separates exploratory findings from confirmatory evidence and prevents
selection of only cases favorable to a particular method.

## 4. Test Suites

### 4.1 Knowledge Gap

These cases require ontology knowledge not explicitly supplied by the minimal
prompt.

Coverage should include:

- aliases and paraphrases that do not repeat ontology labels;
- similar metrics or relations that are easy to confuse;
- class-versus-property distinctions;
- domain and range constraints;
- scope, statistic, measurement method, and time-window combinations;
- distractor concepts that are plausible in networking but invalid for EVSLA.

The suite should not be solvable by copying one fixed mapping table.

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

### 4.3 Ontology Change

These cases use a frozen ontology extension created after the base prompt and
few-shot examples are finalized.

The extension should add several controlled items, such as:

- a new SLA metric;
- a new statistic or scope;
- a new measurement method;
- a relation with explicit domain and range;
- one deprecated or replaced term.

Correct answers must depend on the extension. The new terms must not appear in
the model-facing prompt or few-shot examples. All knowledge-enhanced methods
must receive the same updated ontology source and complete their required
indexing or training before the run.

## 5. Prompt Information Levels

All pipelines use the same generation model, decoding parameters, output
contract, and prompt level within each experimental cell.

### P0: Minimal Schema

Contains only:

- the task definition;
- required top-level JSON-LD shape;
- output-format restrictions;
- a requirement to preserve source meaning and avoid invented values.

It does not include metric-to-CURIE mappings, operator mappings, fixed
statistics, scopes, measurement methods, or few-shot examples.

### P1: Schema Plus Mapping

Contains P0 plus the stable ontology mapping guidance currently embedded in
`evsla_prompt.py`.

It does not include few-shot examples.

### P2: Full Prompt Plus Few-Shot

Contains P1 plus representative few-shot examples.

Few-shot examples must be disjoint from the evaluated cases and must not contain
the ontology-change terms.

Prompt text must be versioned and hashed in each run manifest.

## 6. Discriminative Case-Type Rule

A case type is considered discriminative in Stage 1 when at least one
knowledge-enhanced method shows a practically meaningful difference from
LLM-only.

Primary threshold:

- at least 10 percentage points in the preregistered semantic-quality score;
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
- new extension terms are accepted only when present in the active ontology;
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

Report metrics by pipeline, suite, prompt level, and run:

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

For each method and experimental cell, report:

```text
quality_delta = method_quality - llm_only_quality
token_multiplier = method_online_tokens / llm_only_online_tokens
latency_multiplier = method_latency / llm_only_latency
amortized_cost_delta(N) = method_cost(N) - llm_only_cost(N)
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
- paired per-case differences against LLM-only;
- bootstrap confidence intervals across test cases;
- exact counts of wins, ties, and losses;
- effect sizes and critical-error differences.

Stage 1 findings are exploratory. Only the frozen Stage 2 set is used for
confirmatory claims.

## 11. Reproducibility and Controls

Each run manifest records:

- git commit and dirty-worktree status;
- model and API;
- prompt level, prompt version, and prompt hash;
- few-shot file hash;
- test-suite version and hash;
- ontology and extension hashes;
- retrieval/index/training artifact version;
- temperature and other decoding parameters;
- start time, end time, latency, token usage, and errors;
- random run order.

Pipelines must use the same model and prompt level. Method-specific retrieval
context is allowed, but post-generation repair that changes semantics must be
disabled or scored as part of that method rather than silently normalized.

## 12. Deliverables

The redesign will produce:

- versioned Stage 1 and Stage 2 test suites;
- three versioned prompt configurations;
- structured gold specifications;
- an ontology extension fixture;
- a strict evaluator and human-review rubric;
- run manifests and raw per-run reports;
- quality, stability, token, latency, and amortized-cost comparisons;
- an error taxonomy by suite and pipeline;
- a final conclusion describing where each method is worthwhile.

## 13. Success Criteria

The redesign succeeds when it can support defensible statements such as:

- retrieval is unnecessary for familiar one-metric cases under P2;
- GraphRAG improves ontology-change accuracy under P0 but costs a stated token
  and latency multiplier;
- KGE reduces URI or relation errors for a specific knowledge-gap pattern;
- KAG does or does not improve conditional multi-requirement composition;
- LLM-only is the preferred default for specified regions of the task space;
- a knowledge-enhanced method should be invoked only for identified regions
  where its measured utility is positive.

The experiment is still successful if no enhanced method is worthwhile. A
well-supported negative result is preferable to a ceiling-effect comparison
that cannot distinguish the methods.
