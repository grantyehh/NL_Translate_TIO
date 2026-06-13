# Weak-prompt Retrieval Substitution Experiment — Design Spec

**Date:** 2026-06-13
**Author:** 睿丞 (with Claude Code)
**Status:** Approved design — pending implementation plan

## 1. Research question

Under a **weak system prompt that contains no hand-coded domain knowledge**, can
the retrieval lines (GraphRag / KGE / KAG) reach the output quality of the
**LLM-only strong-prompt ceiling**?

- **If yes** → retrieval can substitute for prompt engineering (the hand-coded
  EVSLA schema in the prompt).
- **If no** → retrieval alone is insufficient; explicit prompt knowledge still matters.

By also running an **LLM-only weak (no-retrieval) floor**, we upgrade the claim
from "substitution vs ceiling" to a quantified **retrieval net lift**:
`lift = (weak + retrieval) − (weak only)`.

### Claim scope (honesty note)

The strong-prompt LLM-only baseline and the weak-prompt retrieval lines use
*different* prompts by design. This experiment therefore measures **"can
retrieval replace hand-coded prompt knowledge"**, NOT "retrieval's marginal
contribution under an identical prompt." Reports must state this framing.

## 2. Weak prompt definition

The strong `build_evsla_system_prompt()` contains: output-format constraint,
`@prefix` list, graph-structure skeleton, metric mappings, target rules,
retrieval note, and a "core semantics in triples" line.

`build_evsla_system_prompt(tc_id, retrieval_mode=None, weak_prompt=False)` gains
a `weak_prompt` flag. Weak vs strong:

| Block | Strong | Weak |
|---|---|---|
| Output-format constraint (only Turtle, never JSON/MD/prose…) | ✅ | ✅ keep |
| Graph-structure skeleton (intent/tenant/service/expectation/target/topology) | ✅ | ❌ **drop** (hand-coded answer) |
| Metric mappings (latency→evsla:latency, 95%→p95, …) | ✅ | ❌ **drop** (domain knowledge) |
| Target rules | ✅ | ❌ **drop** (domain knowledge) |
| retrieval note | ✅ | ✅ keep |
| "Core semantics must be carried by triples" | ✅ | ✅ keep |
| **`@prefix` handling** | full TIO URI list | **split — see below** |

### 2.1 `@prefix` handling (the refined decision)

The `@prefix` block bundles two different things; the weak prompt splits them:

- **(a) Turtle format mechanism** — "every prefix you use must be declared so the
  output is parseable Turtle." This is pure format, unrelated to domain knowledge.
  → **KEEP** as a generic instruction in the weak prompt.
- **(b) Specific TIO namespace URIs** — `icm: / evsla: / quan: / met: / …` with their
  full `http://tio.models.tmforum.org/...` URIs. This *is* the most concentrated
  piece of domain vocabulary, and it is exactly what retrieval is meant to supply
  from the ontology TTL. → **DROP** from the weak prompt.
- **`ex:` instance namespace** (`http://example.org/tio-instance/{tc_id}/`) — this is
  the experiment's own instance convention, NOT domain knowledge, and the evaluator
  scores `intent_uri_contains_case_id` against it. → **KEEP** (with `tc_id`).

Rationale: this isolates **format-correctness** ("model knows it must declare
prefixes") from **knowledge** ("which namespaces / what URIs — must come from
retrieval"). A wrong or missing TIO URI then surfaces as a *true* retrieval-failure
signal (rising `unknown_predicates`/`unknown_types`, or parse failure from an
undeclared CURIE), not as an unfair pure-syntax artifact.

### 2.2 KAG weak prompt

KAG does **not** use `build_evsla_system_prompt`; it has its own registered
`tio_turtle_generator_prompt` (PromptABC) in
`KAG/example_project/solver/tio_turtle_generator.py`, embedding the same domain
sections plus `$query / $content / $tc_id / $few_shot_block`.

Add a parallel `tio_turtle_generator_prompt_weak` class that mirrors the shared
weak prompt content (same dropped sections + same `@prefix` split + same kept
KAG framing/template variables). Building the weak variant is also an opportunity
to align KAG's wording to the shared weak prompt, narrowing the known KAG
prompt-divergence for the weak condition.

## 3. Flag + isolated output (preserve strong baselines)

All four `nl_to_tio.py` gain a `--weak-prompt` flag. When set, outputs route to a
`_weak` namespace; **strong-prompt baselines are never overwritten**:

| Artifact | Strong | Weak |
|---|---|---|
| TTL | `tio_outputs/{llm_only,graphrag,kge,kag}/` | `tio_outputs/{…}_weak/` |
| token log | `phase1/token_usage/token_usage_<line>.json` | `…_<line>_weak.json` |
| phase report | `phase1/phase1_<line>.json` | `phase1/phase1_<line>_weak.json` |

- **LLM-only / GraphRag / KGE**: flag passes `weak_prompt=True` into
  `build_evsla_system_prompt(...)`; output-path / token-path helpers append the
  `_weak` suffix when the flag is set.
- **KAG**: `--weak-prompt` routes output to `tio_outputs/kag_weak/` and tags token
  usage `experiment="kag_weak"`. The generator prompt is switched via a templated
  config variable: `kag_config.template.yaml`'s `generator.generated_prompt.type`
  becomes `{{ TIO_GENERATOR_PROMPT }}` (default `tio_turtle_generator_prompt`); the
  weak run exports `TIO_GENERATOR_PROMPT=tio_turtle_generator_prompt_weak`, re-runs
  `render_config.sh`, then runs `nl_to_tio.py --weak-prompt`. (Fallback if config
  templating proves awkward: override the generator's `generated_prompt` instance
  at runtime in `nl_to_tio.py` — to be settled in the implementation plan.)

## 4. Evaluation + comparison

- `evaluate_ttl.py`: add experiment keys `llm_only_weak`, `graphrag_weak`,
  `kge_weak`, `kag_weak`, each pointing at the corresponding `_weak` output dir and
  writing `phase1_<line>_weak.json`. The evaluator logic is unchanged.
- Comparison: generalize the ad-hoc aggregator already used this session into a
  small script that accepts an arbitrary set of phase1 keys and emits both a
  **quality table** (parse OK %, avg expected coverage, cov=100% count, avg triples,
  intent-URI %, fence count, unknown predicates/types) and a **token table**
  (input / output / total / avg-per-case). Output: `phase1/compare_weak_prompt.txt`.

## 5. Experimental conditions

| Condition | Prompt | Retrieval | Source |
|---|---|---|---|
| LLM-only-strong | strong | none | **ceiling** — existing (this session) |
| GraphRag-strong | strong | typed RDF traversal | existing reference |
| KGE-strong | strong | TransE + link prediction | existing reference |
| KAG-strong | strong (own) | 5-way solver | existing reference |
| **LLM-only-weak** | weak | none | **floor** — new |
| **GraphRag-weak** | weak | typed RDF traversal | new |
| **KGE-weak** | weak | TransE + link prediction | new |
| **KAG-weak** | weak | 5-way solver | new |

Primary comparison: ceiling (LLM-only-strong) vs the three weak-retrieval lines,
with LLM-only-weak as the floor for net-lift computation. Strong retrieval lines
are kept as reference but are not the focus.

## 6. Out of scope

- **Evaluator semantic depth**: the current evaluator already registers weakening
  effects (unknown predicate/type rise, coverage drop, parse failures), so it is
  sufficient for this round; no evaluator redesign here.
- **Cross-method prompt identity in the *strong* condition**: KAG-strong already
  diverges from the shared strong prompt (known gap); not addressed here beyond the
  weak-prompt alignment noted in §2.2.

## 7. Model / fairness invariants

- All conditions share `gpt-5.4` (LLM) and `text-embedding-3-small` (embedding).
- All conditions use the same `few_shot_samples.json` `examples` (4, no slicing).
- The only intended difference across the weak conditions is **prompt (weak) ×
  retrieval (none / GraphRag / KGE / KAG)**.

## 8. Affected files

- `evsla_prompt.py` — add `weak_prompt` param + `@prefix` split.
- `LLM-only/nl_to_tio.py`, `GraphRag/nl_to_tio.py`,
  `KGE/KGE-based-graphrag/nl_to_tio.py` — `--weak-prompt` flag + `_weak` output routing.
- `KAG/nl_to_tio.py` — `--weak-prompt` flag + `_weak` output routing + token tag.
- `KAG/example_project/solver/tio_turtle_generator.py` — `tio_turtle_generator_prompt_weak`.
- `KAG/example_project/kag_config.template.yaml` — templated `generated_prompt.type`.
- `evaluate_ttl.py` — four `_weak` experiment keys.
- new `compare_weak_prompt.py` (or generalized comparator) — multi-key quality + token table.
