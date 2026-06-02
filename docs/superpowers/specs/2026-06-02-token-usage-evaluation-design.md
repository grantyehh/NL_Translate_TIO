# Token Usage Evaluation Design

## Goal

Add token usage evaluation to the Phase 1 experiment so the four NL to TIO JSON-LD methods can be compared by both quality and cost.

The cost comparison must include:

- Online inference token usage per test case.
- Preprocessing or rebuild token usage required to make each method runnable in a new environment.
- Amortized per-case token cost at multiple operating scales.

The token evaluation is a parallel metric. It does not change the existing JSON-LD quality evaluator or its coverage scores.

## Scope

Included:

- LLM-only, GraphRAG, KGE, and KAG token accounting.
- OpenAI chat completion usage.
- OpenAI embedding usage when used by an online or prep stage.
- Per-case online inference telemetry.
- Per-method prep or rebuild telemetry.
- Summary comparison reports.

Excluded:

- Full semantic correctness evaluation beyond the current `evaluate_jsonld.py` scope.
- Downstream TMF chain, device deployment, validation engine, or orchestrator costs.
- Wall-clock benchmarking, except optional timestamps for traceability.

## Cost Ledgers

Token usage is recorded into two separate ledgers.

### Online Inference Ledger

This ledger records token usage that happens for every input intent.

For each test case, online inference starts when the method receives the natural language intent and ends when it writes the final JSON-LD output.

Examples:

- LLM-only: JSON-LD generation call.
- GraphRAG: seed selection LLM call, online embedding call, JSON-LD generation call.
- KGE: online retrieval API calls if any, JSON-LD generation call.
- KAG: solver planning, retrieval, reasoning, and generation calls that happen while solving one test case.

### Prep Ledger

This ledger records token usage required to prepare or rebuild a method so it can run.

Prep cost is included because new environments, ontology changes, KGE artifact rebuilds, and KAG container rebuilds can require rerunning preprocessing.

Examples:

- GraphRAG ontology/index preprocessing when it calls LLM or embedding APIs.
- KGE grounding, text conversion, embedding, or artifact rebuild steps that call APIs.
- KAG KG builder, chunk extraction, summary generation, and index construction API calls.
- LLM-only normally has zero prep token cost.

Prep cost is not mixed directly into the online per-case average. It is reported separately and then amortized.

## Amortized Cost

The amortized per-case token cost at scale `N` is:

```text
amortized_tokens_per_case(N)
= avg_online_tokens_per_case + prep_total_tokens / N
```

The comparison report should show at least:

- `N = 20`, matching the current experiment size.
- `N = 100`, representing a small repeated workload.
- `N = 1000`, representing longer-term service usage.

This avoids binding the interpretation to only the 20-case benchmark while still showing the benchmark-scale cost.

## Output Files

Token telemetry should use fixed Phase 1 paths:

```text
phase1/token_usage_llm_only.json
phase1/token_usage_graphrag.json
phase1/token_usage_kge.json
phase1/token_usage_kag.json
phase1/compare_token_usage.txt
```

The existing quality files remain unchanged:

```text
phase1/phase1_<experiment>.json
phase1/compare_four_way.txt
```

## Telemetry Record Format

Each API call record should include:

```json
{
  "experiment": "graphrag",
  "ledger": "online",
  "case_id": "TC001",
  "stage": "jsonld_generation",
  "model": "gpt-5.4",
  "input_tokens": 5200,
  "output_tokens": 1800,
  "total_tokens": 7000,
  "api": "chat.completions",
  "usage_source": "response.usage"
}
```

For prep calls, `case_id` is omitted or set to `null`.

The implementation should prefer provider-reported usage from API responses. If usage is missing, it may fall back to local estimation, but the record must set `usage_source` accordingly.

## Summary Metrics

The token comparison report should include:

- Cases processed.
- Prep input tokens.
- Prep output tokens.
- Prep total tokens.
- Average online input tokens per case.
- Average online output tokens per case.
- Average online total tokens per case.
- Total online tokens.
- Average API calls per case.
- Amortized tokens per case at `N = 20`.
- Amortized tokens per case at `N = 100`.
- Amortized tokens per case at `N = 1000`.

If quality reports are present, the comparator may also include:

- Tokens per average coverage point.
- Tokens per valid JSON-LD output.

These derived metrics should be labeled clearly because they combine cost telemetry with quality evaluation.

## Method Instrumentation

### LLM-only

Wrap the JSON-LD generation OpenAI call and record the response usage as an online `jsonld_generation` stage.

### GraphRAG

Record:

- Online seed selection LLM usage.
- Online embedding usage used for the test-case retrieval step.
- Online JSON-LD generation usage.

If GraphRAG preprocessing scripts make API calls, record those as prep stages.

### KGE

Record:

- Online JSON-LD generation usage.
- Any online retrieval-stage API usage if present.

KGE rebuild or training-time API calls are prep stages.

### KAG

Record KAG solver internal API usage as online usage for each test case.

KAG is the hardest method to instrument because its solver owns internal LLM calls. The preferred approach is to wrap or hook the KAG LLM provider so every OpenAI-compatible request made during one test case is recorded with the active `case_id`.

KAG kg-builder or index rebuild usage is prep usage.

If complete KAG internal instrumentation is not available in the first implementation, the report must include an `instrumentation_coverage` note so KAG cost is not accidentally interpreted as complete.

## Runner Integration

`run_all_experiments.py` should continue to generate JSON-LD, evaluate quality, and compare quality.

After generation, it should also produce token comparison output from the token telemetry files. The quality workflow must remain runnable even if token telemetry is absent.

Suggested commands:

```bash
python run_all_experiments.py
python run_all_experiments.py --eval-only
python compare_token_usage.py --amortize-over 20 100 1000
```

`--eval-only` should not invent token usage. It should only compare existing telemetry if present.

## Error Handling

- Missing token telemetry files should be reported as missing, not treated as zero.
- Missing usage on one API response should be recorded with `usage_source = "missing"` or an explicit fallback source.
- Failed API calls should record stage, model, and failure metadata if possible, but should not count fake token totals.
- Prep and online records must not be merged silently.

## Testing

Add focused tests for:

- Usage extraction from chat completion responses.
- Usage extraction from embedding responses.
- Ledger aggregation by experiment, case, and stage.
- Amortized cost calculation.
- Comparator behavior when telemetry is missing.
- `--eval-only` behavior with and without existing telemetry.

Use mocked API responses; tests must not call external APIs.

## Open Decisions

- Whether token telemetry should be reset on every run or appended under a run ID.
- Whether prep scripts should be executed by `run_all_experiments.py` or recorded only when explicitly run.
- How deeply to instrument KAG internals in the first implementation.

Default recommendation:

- Reset per-method telemetry on a fresh generation run.
- Keep prep recording explicit and separate from the normal 20-case generation flow.
- Implement complete instrumentation for direct OpenAI calls first, then add KAG provider-level instrumentation as a focused follow-up if needed.
