# Operator Pattern Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach the four TIO-generation lines to encode SLA comparison direction explicitly (a TIO-faithful `log:Condition` applying a `quan:` comparison function), and make the evaluator score it by binding on the shared threshold node.

**Architecture:** Evaluator first (threshold-bound `operator` check, TDD), then teach the pattern in the shared few-shot + both prompt sites, then regenerate + re-evaluate.

**Tech Stack:** Python 3.13, rdflib, unittest.

**Spec:** `docs/superpowers/specs/2026-06-15-operator-pattern-design.md`

---

## File Structure

- Modify `semantic_eval.py` — threshold-bound `operator` check (`_threshold_node`, `_list_members`, `_operator_ok`); drop now-unused `_subgraph_terms`.
- Modify `test_semantic_eval.py` — operator-pattern fixtures + tests.
- Modify `few_shot_samples.json` — condition triad per metric, shared named threshold, `log:`/`met:` prefixes.
- Modify `evsla_prompt.py` — comparison-direction teaching section.
- Modify `KAG/example_project/solver/tio_turtle_generator.py` — same teaching in KAG prompt.

---

### Task 1: Threshold-bound operator check (evaluator)

**Files:**
- Modify: `semantic_eval.py`
- Test: `test_semantic_eval.py`

- [ ] **Step 1: Write the failing tests** (replace the existing `test_operator_detected_when_present` and add fixtures)

```python
# fixture: GOOD_TTL + a TIO-faithful operator condition for the latency metric
OP_TTL = GOOD_TTL.replace(
    "evsla:hasThreshold [ a quan:Quantity ; rdf:value 50 ; quan:unit \"ms\" ] ;",
    "evsla:hasThreshold ex:thr-latency ;") \
  .replace("ex:topology a icm:Context", """ex:cond-latency a log:Condition ;
  quan:smaller ( ex:obs-latency-value ex:thr-latency ) .
ex:obs-latency a met:Observation ; met:observedMetric evsla:latency .
ex:obs-latency-value a quan:Quantity ; met:observedValue ( ex:obs-latency ) .
ex:thr-latency a quan:Quantity ; rdf:value 50 ; quan:unit "ms" .
ex:topology a icm:Context""") \
  .replace("icm:intentElements ex:exp-latency, ex:topology .",
           "icm:intentElements ex:exp-latency, ex:topology, ex:cond-latency .")

OP_PREFIXES = """@prefix log: <http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/> .
@prefix met: <http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/> .
"""

class TestOperator(unittest.TestCase):
    def test_operator_correct_function_bound_to_threshold(self):
        g = Graph(); g.parse(data=OP_PREFIXES + OP_TTL, format="turtle")
        self.assertEqual(score_semantics(g, GOLD_TC001)["dimensions"]["operator"], 1.0)
        # threshold still read from the now-named node
        self.assertEqual(score_semantics(g, GOLD_TC001)["dimensions"]["threshold"], 1.0)

    def test_operator_wrong_function_scores_zero(self):
        wrong = (OP_PREFIXES + OP_TTL).replace("quan:smaller", "quan:atLeast")
        g = Graph(); g.parse(data=wrong, format="turtle")
        self.assertEqual(score_semantics(g, GOLD_TC001)["dimensions"]["operator"], 0.0)

    def test_operator_absent_scores_zero(self):
        g = Graph(); g.parse(data=GOOD_TTL, format="turtle")   # no condition
        self.assertEqual(score_semantics(g, GOLD_TC001)["dimensions"]["operator"], 0.0)
```

Delete the old `test_operator_detected_when_present` test (it used the rejected subgraph approach).

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest test_semantic_eval.TestOperator -v`
Expected: FAIL (operator returns 0.0 for the correct graph because the old check looked under the expectation subgraph, not at the sibling condition).

- [ ] **Step 3: Implement** — in `semantic_eval.py`:

Add helpers (after `_obj`):
```python
def _threshold_node(g, target):
    for p in (EVSLA.hasThreshold, ICM.valuesOfTargetProperty):
        q = _obj(g, target, p)
        if q is not None and _obj(g, q, RDF.value) is not None:
            return q
    return None

def _list_members(g, head):
    out, seen = [], set()
    while head is not None and head != RDF.nil and head not in seen:
        seen.add(head)
        first = _obj(g, head, RDF.first)
        if first is not None:
            out.append(first)
        head = _obj(g, head, RDF.rest)
    return out

def _operator_ok(g, expected_fn, thr_node):
    if expected_fn is None or thr_node is None:
        return 0.0
    for _s, lst in g.subject_objects(expected_fn):
        if thr_node in _list_members(g, lst):
            return 1.0
    return 0.0
```
Change `_threshold` to reuse the node:
```python
def _threshold(g, target):
    q = _threshold_node(g, target)
    if q is not None:
        return _obj(g, q, RDF.value), _obj(g, q, QUAN.unit)
    return None, None
```
In `_score_one_metric`, replace the operator line:
```python
    expected_fn = OPERATOR_FN.get(pm.get("operator"))
    d["operator"] = _operator_ok(g, expected_fn, _threshold_node(g, b["target"]))
```
Delete the now-unused `_subgraph_terms` function.

- [ ] **Step 4: Run all evaluator tests**

Run: `python3 -m unittest test_semantic_eval -v`
Expected: PASS (all, including the 3 new operator tests).

- [ ] **Step 5: Commit**

```bash
git add semantic_eval.py test_semantic_eval.py
git commit -m "feat(eval): threshold-bound operator check for log:Condition pattern"
```

---

### Task 2: Teach the pattern in the shared few-shot

**Files:**
- Modify: `few_shot_samples.json`

- [ ] **Step 1: Edit each of the 4 examples' `turtle`.** For every metric in the example:
  1. Add `@prefix log: <http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/> .` and `@prefix met: <http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/> .` to the prefix block.
  2. Change the threshold from an inline blank node to a shared named node `ex:thr-<metric>` referenced by both `evsla:hasThreshold` and `icm:valuesOfTargetProperty`, with `rdf:value` + `quan:unit`.
  3. Add the triad and the condition; add the condition id to `icm:intentElements`:
```turtle
ex:cond-<metric> a log:Condition ;
  <quan-fn> ( ex:obs-<metric>-value ex:thr-<metric> ) .
ex:obs-<metric> a met:Observation ; met:observedMetric evsla:<metric> .
ex:obs-<metric>-value a quan:Quantity ; met:observedValue ( ex:obs-<metric> ) .
```
     where `<quan-fn>` = `quan:smaller` for latency/packet loss (LESS_THAN) and `quan:atLeast` for guaranteed bandwidth (GREATER_THAN_OR_EQUAL).

- [ ] **Step 2: Verify the few-shot examples still parse as Turtle**

Run:
```bash
python3 -c "
import json
from rdflib import Graph
d=json.load(open('few_shot_samples.json'))
for i,ex in enumerate(d['examples'],1):
    g=Graph(); g.parse(data=ex['turtle'], format='turtle')
    fns=[str(p).split('/')[-1] for p in set(g.predicates()) if 'QuantityOntology' in str(p) and any(x in str(p) for x in ['smaller','atLeast','greater','atMost'])]
    print(f'example {i}: parses OK, comparison fns used = {fns}')
"
```
Expected: all 4 parse; examples report `smaller` and/or `atLeast`.

- [ ] **Step 3: Commit**

```bash
git add few_shot_samples.json
git commit -m "feat(fewshot): add TIO-faithful comparison-direction condition per metric"
```

---

### Task 3: Teach the pattern in both prompts

**Files:**
- Modify: `evsla_prompt.py`
- Modify: `KAG/example_project/solver/tio_turtle_generator.py`

- [ ] **Step 1: Add a "Comparison direction" block to `evsla_prompt.py`.** In `build_evsla_system_prompt`, before the final `Core semantics...` line, insert:
```python
Comparison direction (required, explicit — do not rely on comments):
- Make the threshold a shared named node ex:thr-<metric> used by both evsla:hasThreshold and icm:valuesOfTargetProperty.
- For each metric add a condition as an intent element:
    ex:cond-<metric> a log:Condition ; <fn> ( ex:obs-<metric>-value ex:thr-<metric> ) .
    ex:obs-<metric> a met:Observation ; met:observedMetric evsla:<metric> .
    ex:obs-<metric>-value a quan:Quantity ; met:observedValue ( ex:obs-<metric> ) .
  and list ex:cond-<metric> in ex:intent icm:intentElements.
- <fn>: latency/packet_loss -> quan:smaller ; guaranteed_bandwidth -> quan:atLeast.
- Declare @prefix log: <.../LogicalOperators/> and @prefix met: <.../MetricsAndObservations/>.
```
(Use the full URIs for log: and met: as in the other prefixes.)

- [ ] **Step 2: Mirror the same instruction in the KAG prompt template** (`tio_turtle_generator.py`, inside `template_en`, before the `Few-shot Turtle examples` line). Same text as Step 1.

- [ ] **Step 3: Smoke-check the prompt renders**

Run: `python3 -c "from evsla_prompt import build_evsla_system_prompt as b; print('quan:smaller' in b('TC001'))"`
Expected: `True`.

- [ ] **Step 4: Commit**

```bash
git add evsla_prompt.py KAG/example_project/solver/tio_turtle_generator.py
git commit -m "feat(prompt): teach explicit comparison-direction condition pattern"
```

---

### Task 4: Regenerate, re-evaluate, report

**Files:** none (run only)

- [ ] **Step 1: Regenerate the three main lines** (system python3, env loaded):
```bash
set -a && source .env && set +a
( cd LLM-only && python3 nl_to_tio.py ) && ( cd GraphRag && python3 nl_to_tio.py ) && ( cd KGE/KGE-based-graphrag && python3 nl_to_tio.py )
```

- [ ] **Step 2: Regenerate KAG** (KAG venv; Docker stack already up, KG populated):
```bash
set -a && source .env && set +a
export GRAPHRAG_LLM_MODEL=gpt-5.4 GRAPHRAG_EMBEDDING_MODEL=text-embedding-3-small
( cd KAG/example_project && bash render_config.sh )
( cd KAG && /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/KAG/.venv/bin/python nl_to_tio.py )
```

- [ ] **Step 3: Re-evaluate + rebuild comparison**
```bash
python3 run_all_experiments.py --eval-only
```

- [ ] **Step 4: Report operator cross-case rates** (compare to before = operator 0/20):
```bash
python3 -c "
import json
for line in ['llm_only','graphrag','kge','kag']:
    d=json.load(open(f'phase1/phase1_{line}.json'))
    sem=[x['semantic'] for x in d if x.get('semantic')]
    op=sum(s['dimensions']['operator'] for s in sem)/len(sem)
    comp=sum(s['composite'] for s in sem)/len(sem)
    print(f'{line:9} operator={op:.2f}  composite={comp:.4f}')
"
```

---

## Self-Review notes

- **Spec coverage:** §3 pattern → Task 2/3 (few-shot + prompts); §4.3 evaluator → Task 1; §5 run/report → Task 4. Both prompt sites covered (Task 3). Multi-metric (TC020) handled by "per metric" wording in Task 2.
- **Type consistency:** `_threshold_node` / `_list_members` / `_operator_ok` used consistently; `_threshold` refactored to reuse `_threshold_node`; `_subgraph_terms` removed and no longer referenced.
- **Operator map:** quan:smaller (LESS_THAN), quan:atLeast (GREATER_THAN_OR_EQUAL) — matches `OPERATOR_FN` and gold operators present in the 20 cases.
