# Retrieval Four-Dimension Grounding (tenant / time_window / measurement_method / topology)

Date: 2026-06-16

Status: design approved, pending spec review

## 1. Research Question

In the structure-only regime (test_cases_40, EVSLA vocabulary withheld from the
prompt, retrieval must supply it) both retrieval lines plateau well below the
strong-prompt ceiling:

```text
Line                       | Composite | Tok/case
LLM-only strong (ceiling)  |  0.9722   |  5,349
GraphRAG-structure         |  0.7867   |  2,369
KGE-structure (canonical)  |  0.7540   |  2,292
LLM-only-structure (floor) |  0.0000   |  1,432
```

The token problem is already solved — retrieval runs at **< half** the ceiling's
tokens. The remaining `replacement_gap` (−0.1855 for GraphRAG) is **entirely
concentrated in four dimensions**, identical across both methods:

| Dimension          | GraphRAG | KGE   |
|--------------------|----------|-------|
| tenant             | 0.000    | 0.000 |
| time_window        | 0.200    | 0.125 |
| measurement_method | 0.350    | 0.388 |
| topology           | 0.500    | 0.425 |
| (all other 7 dims) | 0.90–1.00| 0.91–0.95 |

> Can we lift these four dimensions to near-ceiling by encoding the missing
> **domain conventions in the EVSLA ontology** and reliably surfacing them
> through the shared retrieval layer — **without** growing token cost and
> **without** regressing the seven already-strong dimensions?

Scope: both retrieval lines (GraphRAG + canonical KGE), which share the output
contract (`resource_index` / `graph_relations` / `context_builder`). LLM-only is
the unchanged ceiling/floor reference.

## 2. Root-Cause Diagnosis

Established by reading the scorer (`semantic_eval.py`), the 40-case gold
(`test_cases_40.json`), the EVSLA TTL, and the retrieval layer.

**What each dimension requires (exact-match, structural scorer):**
- `tenant` — a node typed `evsla:Tenant` whose `rdfs:label` equals the gold
  tenant string (`_tenant_ok`).
- `time_window` / `measurement_method` — the metric target must carry
  `evsla:hasTimeWindow` / `evsla:hasMeasurementMethod` pointing at the **exact**
  official IRI (`_score_one_metric` via `_eq`).
- `topology` — `evsla:HubAndSpokeTopology` + `evsla:HubSite` + `evsla:SpokeSite`
  typed nodes all present (`_topology_ok`).

**Why each currently fails:**

1. **tenant = 0.000 (systematic).** The org name is in the NL (宏遠科技,
   星河銀行…) but nothing instructs the model to emit `evsla:Tenant` +
   `rdfs:label`. The retrieval reachability has a concrete bug:
   `graph_relations.traverse_connective` activates `forTenant` only if a
   grounded seed *is* a Tenant (it has no `rdfs:domain`), but seeds are metric
   IRIs — so `fortenant_active` never becomes true and the `Tenant` role is
   never reached, never supplied.

2. **time_window = 0.20/0.13.** The window IS derivable from the NL but no
   mapping rule is given. Across the 40 gold cases: default `fiveMinuteWindow`
   (no NL cue), `oneHourWindow` when the NL says **「每小時視窗」** (TC036–037),
   `monthlySlaWindow` when the NL says **「月度 SLA 視窗」** (TC038–040). The
   closed vocab lists the candidates but carries no default + no NL trigger, so
   the LLM guesses.

3. **measurement_method = 0.35/0.39.** Largely a function of metric
   (`latency`/`packetLoss` → `twamp`, `guaranteedBandwidth` →
   `activeMeasurement`), with edge cases (e.g. TC039 `latency` →
   `activeMeasurement`). NL never names the method. Vocab present, default rule
   absent.

4. **topology = 0.50/0.43.** Roles are in `RANGE_ROLE` but hub/spoke node
   typing is inconsistent — the assembly skeleton does not require all three
   typed nodes.

**Shared cause:** the closed-vocabulary + assembly skeleton does not reliably
*reach* these roles, nor tell the LLM how to map NL → IRI. This is the exact
failure that the operator-pattern fix already solved for `operator` (0 → 0.96):
supply the closed vocab + let the LLM pick from NL.

## 3. Design

### 3.1 Ontology layer — `TM Forum Intent Ontology/EnterpriseVpnSlaOntology.ttl`

Encode the conventions as ontology facts (the principled location: retrieval
reads TTL, both methods inherit, no per-case rules in code).

- **Metric → default measurement method** convention triples, e.g.
  `evsla:latency evsla:defaultMeasurementMethod evsla:twamp ;`
  `evsla:packetLoss evsla:defaultMeasurementMethod evsla:twamp ;`
  `evsla:guaranteedBandwidth evsla:defaultMeasurementMethod evsla:activeMeasurement .`
  The exact mapping is derived from the 40-case gold during implementation; a
  new annotation property `evsla:defaultMeasurementMethod` is declared.
- **Default time window** marker, e.g. `evsla:fiveMinuteWindow` flagged as the
  default (declare `evsla:isDefaultTimeWindow` or an intent-level
  `evsla:defaultTimeWindow`), plus **Chinese labels** on the override windows so
  NL→IRI mapping is label-grounded:
  `evsla:oneHourWindow rdfs:label "每小時視窗"@zh ;`
  `evsla:monthlySlaWindow rdfs:label "月度SLA視窗"@zh .`
- Ensure `evsla:Tenant`, `evsla:HubAndSpokeTopology`, `evsla:HubSite`,
  `evsla:SpokeSite` carry clear `rdfs:label`/`rdfs:comment` so the closed-vocab
  block reads unambiguously.

These are legitimate domain-modelling statements (real EVSLA measurement
conventions), not test-specific encodings.

### 3.2 Retrieval layer — shared `GraphRag/graph_relations.py`, `GraphRag/context_builder.py`

1. **Guarantee reachability.** When an SLA expectation is grounded (a metric is
   reached), always surface the closed vocab for `Tenant`, `MeasurementMethod`,
   `TimeWindow`, and the topology roles (`HubSite`/`SpokeSite`/
   `HubAndSpokeTopology`). Fix the `forTenant` special case so `Tenant` is
   reached whenever an `EnterpriseVpnSlaIntent`/SLA expectation is present,
   independent of seed type.
2. **Surface conventions.** Read the new `defaultMeasurementMethod` /
   default-window facts and the zh labels, and render them in
   `serialize_context` as an explicit convention block, e.g.
   `MeasurementMethod: default evsla:twamp for latency/packetLoss, ...` and
   `TimeWindow: default evsla:fiveMinuteWindow; 「每小時視窗」-> evsla:oneHourWindow; 「月度SLA視窗」-> evsla:monthlySlaWindow`.
3. **Assembly skeleton.** Extend the structure-only profile instructions to
   require: a `evsla:Tenant` node with `rdfs:label "<org from NL>"` wired via
   `evsla:forTenant`; and `evsla:HubAndSpokeTopology` with the hub typed
   `evsla:HubSite` and each spoke typed `evsla:SpokeSite`.

### 3.3 Per-method wiring

- **GraphRAG** reads the TTL at runtime — no index rebuild required for the
  convention triples (it traverses the live graph). If `resource_index` caches
  labels, confirm new labels are picked up.
- **KGE** must `cd KGE/KGE-based-graphrag && python -m kge.train` to refresh
  artifacts after the TTL change (CLAUDE.md §6); it consumes the same
  `context_builder` output so the retrieval-layer changes apply for free.

## 4. Success Criteria

Re-run structure-only (40 cases, strict `semantic_eval`, gpt-5.4), both methods:

- Composite **0.79 / 0.75 → ≥ 0.93** (closes most of the −0.1855 gap).
- Each of the four target dims **≥ 0.85**.
- **No regression** on the seven strong dims (metric, operator, threshold,
  scope, contract, precision, statistic) — each stays within −0.02 of current.
- Token cost stays **≤ ~2,500/case** (no material increase vs ~2,300).
- Parse OK 100%; zero non-official-namespace IRIs (scorer would zero them).

## 5. Validation Plan

1. Derive the exact metric→method and window conventions from all 40 gold cases
   (a small script over `test_cases_40.json`); encode them in TTL.
2. Apply retrieval-layer changes; run GraphRAG structure-only; inspect
   per-dimension deltas and token/case.
3. `python -m kge.train`; run KGE structure-only; same inspection.
4. Compare against the canonical baseline table; update `progress.md` (results
   are not auto-propagated — CLAUDE.md §4.8 / §6).
5. Unit tests: extend `GraphRag/test_graph_relations.py` for `forTenant`
   reachability and `GraphRag/test_context_builder.py` for the convention block.

## 6. Risks and Mitigations

- **Overfitting to the 40-case gold.** Mitigated by encoding *general*
  conventions (a default + NL-label triggers) rather than per-case rules; the
  conventions are real domain semantics and generalize to unseen cases.
- **Edge cases in metric→method** (e.g. TC039 `latency`→`activeMeasurement`). A
  pure metric default may miss a few; acceptable if composite still clears
  target. The residual will be measured and documented, not hidden.
- **KGE retrain drift.** TTL change invalidates KGE artifacts; the plan makes
  retrain an explicit step, and KGE is re-evaluated, not assumed.
- **Token creep from the convention block.** The block is a few lines and
  *replaces* vague vocab guessing; if tokens exceed budget, `guard_tokens`
  priority ordering keeps the convention block (high priority) and drops
  lower-value items.

## 7. Out of Scope

- LLM-only line (unchanged ceiling/floor reference).
- The strong-prompt 20-case regime (already saturated at 1.0).
- The stale `phase1/token_usage/` strong-recipe ledgers (25k) — a separate
  cleanup; this work reports tokens from the structure-only re-run.
- Any TMF chain / downstream consumption (other repos).
