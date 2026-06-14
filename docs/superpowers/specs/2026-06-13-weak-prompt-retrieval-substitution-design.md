# Recipe CP Comparison: Prompt-Engineering vs Retrieval — Design Spec

**Date:** 2026-06-13 (revised 2026-06-15 to a two-arm CP framing)
**Author:** 睿丞 (with Claude Code)
**Status:** Approved design — pending implementation plan

## 1. Purpose

Compare two end-to-end **recipes** for NL → TIO Turtle and decide which has the
better **cost-performance (CP)** — quality per token:

- **Arm 1 — "prompt-engineering" recipe (LLM-only):** strong system prompt +
  strong few-shot + **no retrieval**. All domain knowledge is hand-coded into the
  prompt and examples.
- **Arm 2 — "retrieval" recipe:** **weak** system prompt + **no few-shot** +
  retrieval (GraphRag / KGE / KAG). Hand-coded domain knowledge is removed; the
  model must get EVSLA vocabulary/structure from retrieval.

This is deliberately an **approach-vs-approach** comparison (multiple variables
differ at once), because the question is "which whole strategy is worth it," not
an isolated single-variable ablation.

A **floor** condition (weak prompt + no few-shot + **no retrieval**) isolates how
much retrieval adds on top of the bare weak base.

### Conclusion shape
For each line, plot/quote **quality (semantic composite + key dimensions)** against
**token cost**. Does LLM-only-strong dominate (better quality at comparable/less
cost), or does a weak+retrieval line give comparable quality far cheaper? CP is the
verdict.

## 2. Conditions

| Condition | System prompt | Few-shot | Retrieval | Role |
|---|---|---|---|---|
| **LLM-only-strong** | strong | strong | none | **Arm 1** (prompt-engineering recipe) |
| **LLM-only-weak** | weak | none | none | **Floor** (no engineering, no retrieval) |
| **GraphRag-weak** | weak | none | typed RDF traversal | **Arm 2** |
| **KGE-weak** | weak | none | TransE + link prediction | **Arm 2** |
| **KAG-weak** | weak | none | 5-way solver | **Arm 2** |

Arm 1 reuses the existing strong run (strong prompt + the operator-enriched
few-shot). The strong-prompt retrieval lines are *not* part of this experiment.

## 3. Weak prompt definition

`build_evsla_system_prompt(tc_id, retrieval_mode=None, weak_prompt=False)` gains a
`weak_prompt` flag. Weak **drops all hand-coded domain knowledge**:

| Block | Strong | Weak |
|---|---|---|
| Output-format constraint (only Turtle, never JSON/MD/prose…) | ✅ | ✅ keep |
| Generic "declare every prefix you use" | (implicit) | ✅ keep |
| `ex:` instance namespace with `tc_id` | ✅ | ✅ keep (evaluator scores `intent_uri`) |
| retrieval note | ✅ | ✅ keep |
| "core semantics in triples" line | ✅ | ✅ keep |
| Graph-structure skeleton | ✅ | ❌ drop |
| Metric mappings (latency→evsla:latency, 95%→p95…) | ✅ | ❌ drop |
| Target rules | ✅ | ❌ drop |
| **Comparison-direction (operator) section** | ✅ | ❌ drop |
| Specific TIO `@prefix` URI list (icm/evsla/quan/log/met…) | ✅ | ❌ drop |

The weak prompt thus contains **no EVSLA class/property names, no metric mappings,
no structure, no operator pattern, no TIO namespace URIs** — only "produce
parseable TIO Turtle for this intent, declare the prefixes you use, ground it in
the retrieval context." Everything domain-specific must come from retrieval.

## 4. Few-shot removal (the key change)

In weak mode, **few-shot is fully removed** — not weakened, removed. The
`--weak-prompt` flag disables few-shot loading so the user message carries only the
NL intent (and, for retrieval lines, the retrieval context). No EVSLA example is
shown. Rationale: with the strong few-shot kept, the 4 examples leak the entire
EVSLA structure (incl. the operator condition), so weakening only the system prompt
would test nothing. Removing few-shot makes **retrieval the sole domain source** in
Arm 2, and leaves the floor with no domain source at all.

## 5. Output isolation (preserve strong baselines)

`--weak-prompt` routes to a `_weak` namespace; strong baselines are untouched:

| Artifact | Strong | Weak |
|---|---|---|
| TTL | `tio_outputs/<line>/` | `tio_outputs/<line>_weak/` |
| token log | `phase1/token_usage/token_usage_<line>.json` | `…_<line>_weak.json` |
| phase report | `phase1/phase1_<line>.json` | `phase1/phase1_<line>_weak.json` |

- LLM-only / GraphRag / KGE: `--weak-prompt` → `weak_prompt=True` into
  `build_evsla_system_prompt(...)`, few-shot disabled, `_weak` output paths.
- KAG: a parallel weak generator prompt (`tio_turtle_generator_prompt_weak`,
  mirroring the shared weak prompt — dropped sections, no operator, no TIO URIs),
  selected via a templated `generator.generated_prompt.type` in
  `kag_config.template.yaml` (`{{ TIO_GENERATOR_PROMPT }}`), few-shot disabled,
  `_weak` output + `experiment="kag_weak"` token tag.

## 6. Measurement — stricter semantic evaluator + token

Use the **graph-binding semantic evaluator** (`semantic_eval.py`, already built),
not the old format+coverage view. `evaluate_ttl.py` already attaches the `semantic`
block; add experiment keys `llm_only_weak`, `graphrag_weak`, `kge_weak`,
`kag_weak`. The comparison reports, per condition:

- **Quality:** semantic composite + per-dimension rates (metric / threshold /
  statistic / scope / method / time_window / operator / tenant / topology /
  contract / precision), plus parse-OK as a gate.
- **Cost:** input / output / total tokens, avg per case (and KGE/KAG prep where
  relevant).
- **CP:** quality-vs-token for Arm 1 vs each Arm 2 line, with the floor as the
  no-retrieval reference.

Output: `phase1/output_quality/compare_recipe_cp.txt` (extend the existing
multi-key comparator).

## 7. Honest prediction (this is the finding the experiment buys)

TIO's TTLs define **vocabulary** but contain **no worked assembly example**
(intent→expectation→target wiring, the operator condition). Retrieval reads those
TTLs, so it can supply **vocabulary** (`evsla:latency`, `quan:smaller` exist) but
**not assembly** (how to wire them). Expected: Arm 2 holds up on vocabulary-ish
dimensions (metric/scope/statistic if retrieval surfaces the terms) but **drops on
the assembly dimensions** (structure/contract/topology) and especially
**operator ≈ 0** (our convention is absent from the TTLs, so retrieval cannot teach
it). The CP comparison quantifies exactly this: retrieval saves prompt-engineering
effort but may not buy structural correctness — and never buys the un-exampled
operator pattern.

## 8. Fairness invariants

- All conditions share `gpt-5.4` + `text-embedding-3-small`.
- The intended differences are exactly: prompt strength (strong/weak), few-shot
  (present/absent), retrieval (none/GraphRag/KGE/KAG) — bundled per recipe by design.

## 9. Out of scope

- Strong-prompt retrieval lines (not part of the 2-arm CP question; kept only as
  prior reference results).
- Evaluator changes beyond adding the `_weak` keys (the semantic evaluator is reused
  as-is).
- KAG re-indexing (KG already populated; only KAG weak generation + prompt).

## 10. Affected files

- `evsla_prompt.py` — `weak_prompt` flag (drop domain blocks incl. operator + TIO URIs).
- `LLM-only/nl_to_tio.py`, `GraphRag/nl_to_tio.py`,
  `KGE/KGE-based-graphrag/nl_to_tio.py` — `--weak-prompt` (weak prompt + disable
  few-shot + `_weak` output routing).
- `KAG/nl_to_tio.py` — `--weak-prompt` (disable few-shot + `_weak` output + token tag).
- `KAG/example_project/solver/tio_turtle_generator.py` — `tio_turtle_generator_prompt_weak`.
- `KAG/example_project/kag_config.template.yaml` — templated `generated_prompt.type`.
- `evaluate_ttl.py` — four `_weak` experiment keys.
- `compare_reports.py` (or a new `compare_recipe_cp.py`) — multi-key quality (semantic)
  + token CP table over the 5 conditions.
