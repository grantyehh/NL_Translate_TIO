# Operator Pattern (explicit comparison direction) — Design Spec

**Date:** 2026-06-15
**Author:** 睿丞 (with Claude Code)
**Status:** Approved design — pending implementation plan

## 1. Purpose

Today the comparison **direction** of every SLA target ("latency must stay
**below** 50 ms", "bandwidth **at least** 100 Mbps") lives only in an English
`rdfs:comment`; no triple expresses it. The semantic evaluator's `operator`
dimension is therefore 0/20 across all four lines — because nothing in the prompt
or few-shot ever asks the model to encode it.

This spec makes explicit comparison-direction encoding part of the **canonical
output shape**: it adds a TIO-faithful condition pattern to the few-shot gold and
the generation prompts, and adapts the evaluator to bind it. The broader goal is
to test whether the retrieval methods let the model reproduce a complex-but-correct
TIO construct stably — direction is the first such construct.

## 2. Design principle — strictly follow TIO's documented semantics

TIO's 16 TTLs define the **building blocks** but contain **no worked example** of
applying a comparison function to an SLA threshold. So the canonical assembly is
derived strictly from each term's documented domain/range/semantics (below), with
**zero looseness**. Retrieval grounds the vocabulary/semantics; the few-shot
teaches the assembly TIO itself never demonstrates.

Documented semantics used:
- `fun:Function` ⊑ `rdf:Property`; "instances can be used **as properties**; the
  range … is a **list** … the list of function arguments"; result is associated
  with the subject. → a comparison function is a **predicate** with an `rdf:List`
  object.
- `quan:smaller`/`greater`/`atMost`/`atLeast`/`exactly`: `fun:Function`,
  `fun:arityMin 2`, `fun:argumentTypes ( quan:Quantity )` → 2 `quan:Quantity` args.
- `log:Condition` ⊑ `icm:IntentElement` → a condition is an intent element,
  attached via `icm:intentElements` (domain `icm:Intent`, range `icm:IntentElement`).
- `met:Observation`; `met:observedMetric` (domain `met:Observation`, range
  `met:Metric`) → ties an observation to the metric property; `met:observedValue`
  (a function) → yields the observation's value as a `quan:Quantity`.

> Rejected: `insp:applicableIf` — real, but `rdfs:domain insp:ContentTemplate`
> (intent-specification templates), so attaching it to an `evsla:SlaExpectation`
> violates its domain. Not used.

## 3. The canonical pattern (per metric)

```turtle
ex:intent a icm:Intent, evsla:EnterpriseVpnSlaIntent ;
  icm:intentElements ex:exp-latency, ex:topology, ex:cond-latency .   # condition is an intent element

ex:cond-latency a log:Condition ;
  quan:smaller ( ex:obs-latency-value ex:thr-latency ) .              # observed value  <  threshold

ex:obs-latency a met:Observation ; met:observedMetric evsla:latency .
ex:obs-latency-value a quan:Quantity ; met:observedValue ( ex:obs-latency ) .   # the value (quan:Quantity)

ex:tgt-latency a icm:Target ;
  evsla:hasMetric evsla:latency ;
  evsla:hasThreshold ex:thr-latency ;
  icm:valuesOfTargetProperty ex:thr-latency ;
  evsla:hasStatistic evsla:p95 ; evsla:hasScope evsla:hubToAllSpokes ;
  evsla:hasMeasurementMethod evsla:twamp ; evsla:hasTimeWindow evsla:fiveMinuteWindow .

ex:thr-latency a quan:Quantity ; rdf:value 50 ; quan:unit "ms" .       # shared by hasThreshold AND the condition
```

Key points:
- Both `quan:smaller` arguments are `quan:Quantity` (observed value + threshold) →
  zero `argumentTypes` looseness.
- The condition binds to its metric by **sharing the threshold node**
  (`ex:thr-latency` is the object of both `evsla:hasThreshold` and the condition's
  argument list) — this is what the evaluator keys on.
- **Threshold becomes a named node** `ex:thr-<metric>` (was an inline blank node) so
  it can be shared. `rdf:value` + `quan:unit` are unchanged, so the existing
  `threshold` dimension still reads them.
- Operator → function map: LESS_THAN→`quan:smaller`, LESS_THAN_OR_EQUAL→`quan:atMost`,
  GREATER_THAN→`quan:greater`, GREATER_THAN_OR_EQUAL→`quan:atLeast`, EQUAL→`quan:exactly`.
- Multi-metric cases (TC020): one condition + observation + value triad **per metric**.

## 4. Changes

### 4.1 Few-shot (`few_shot_samples.json`)
All 4 examples: per metric, add the condition + observation + observed-value triad,
turn the threshold into a shared named node, and add the condition to
`icm:intentElements`. Add the `log:` and `met:` prefixes to each example.

### 4.2 Generation prompts (both teaching sites)
- `evsla_prompt.py` (LLM-only / GraphRag / KGE): add a "Comparison direction"
  section showing the condition pattern + the operator→function map, and require a
  named shared threshold node.
- `KAG/example_project/solver/tio_turtle_generator.py` (`tio_turtle_generator_prompt`
  template, used only by KAG): mirror the same instruction (KAG does not use
  `evsla_prompt`).

### 4.3 Evaluator (`semantic_eval.py`)
The `operator` check changes from "function IRI anywhere under the expectation
subgraph" to **threshold-bound condition matching**:
- Get the metric's threshold node (object of `evsla:hasThreshold` /
  `icm:valuesOfTargetProperty`).
- `operator = 1.0` iff there exists a triple `(?cond, <expected_fn>, ?list)` whose
  `rdf:List` members include that threshold node; else 0.0.
- This binds the condition to the correct metric via the shared threshold node and
  matches the **specific** expected function (wrong function → 0).
- Helpers: `_threshold_node(g, target)` (return the node, not just value/unit;
  `_threshold` reuses it) and `_list_members(g, head)` (walk `rdf:first`/`rdf:rest`).

No other dimension changes. The condition is a `log:Condition`, not a
`PropertyExpectation`, so `extract_bindings` skips it → no spurious binding, no
false hallucination, contract/precision unaffected.

## 5. Run + reporting

1. Apply 4.1–4.3; `python3 -m unittest test_semantic_eval` green (incl. new
   operator-pattern tests: correct → 1.0, wrong function → 0.0, missing → 0.0).
2. Regenerate all four lines (real LLM cost, ~ prior run) and re-evaluate
   (`run_all_experiments.py`), or per-line generation + `--eval-only`.
3. Report operator cross-case rates per line: does it move off 0/20, and which
   method reproduces the pattern most stably? `2e20eb8` is the "before" (operator
   not in gold).

## 6. Out of scope

- A full TIO-faithfulness audit of the *entire* output shape (statistic/scope/etc.
  modeling) — a possible follow-up spec; this spec is operator/direction only.
- Changing weights or other dimensions.
- KAG re-indexing (KG already populated; only KAG generation + its prompt change).

## 7. Affected files

- `few_shot_samples.json` — condition triad per metric + shared threshold + prefixes.
- `evsla_prompt.py` — comparison-direction teaching section.
- `KAG/example_project/solver/tio_turtle_generator.py` — same teaching in the KAG prompt.
- `semantic_eval.py` — threshold-bound `operator` check (`_threshold_node`,
  `_list_members`, `_operator_ok`).
- `test_semantic_eval.py` — operator-pattern unit tests.
- `docs/superpowers/specs/2026-06-14-stricter-semantic-evaluator-design.md` — note
  §3.1 operator is now taught (was 0/20 finding).
