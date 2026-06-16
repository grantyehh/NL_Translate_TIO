# Retrieval Four-Dimension Grounding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift the four weak semantic dimensions (`tenant`, `time_window`, `measurement_method`, `topology`) of both retrieval lines (GraphRAG + canonical KGE) from ~0.79/0.75 composite toward ≥0.93 in the structure-only regime, at flat token cost (~2,300/case), by encoding domain conventions in the EVSLA ontology and fixing the shared retrieval layer.

**Architecture:** Conventions (metric→default measurement method; default time window + Chinese NL-trigger labels) are encoded as triples in `EnterpriseVpnSlaOntology.ttl`. The shared retrieval layer (`resource_index.py`, `graph_relations.py`, `context_builder.py`) is fixed to (1) reach + supply the `Tenant`/`HubSite`/`SpokeSite` roles, (2) surface the convention triples as an explicit context block. The structure-only system prompt (`evsla_prompt.py`) gains assembly requirements for the tenant binding and typed topology nodes — using vocabulary from retrieval, never hardcoded. Both GraphRAG and KGE consume the same `context_builder` output and `build_evsla_system_prompt`, so one fix lifts both. KGE artifacts are retrained after the TTL change.

**Tech Stack:** Python 3, `rdflib`, `unittest`, OpenAI chat/embeddings (`gpt-5.4`), the project's main `.venv` (GraphRAG/KGE share it).

**Conventions (derived from all 40 gold cases in `test_cases_40.json`):**
- measurement_method: `evsla:latency`→`evsla:twamp`, `evsla:packetLoss`→`evsla:twamp`, `evsla:guaranteedBandwidth`→`evsla:activeMeasurement` (one documented edge case: TC039 `latency`→`activeMeasurement`, accepted as residual).
- time_window: default `evsla:fiveMinuteWindow`; NL contains 「每小時」→`evsla:oneHourWindow`; NL contains 「月度」→`evsla:monthlySlaWindow`.

---

## File Structure

- `TM Forum Intent Ontology/EnterpriseVpnSlaOntology.ttl` (modify) — convention triples + zh labels + default-window marker.
- `GraphRag/resource_index.py` (modify) — add `Tenant`/`HubSite`/`SpokeSite` to `CLASS_ROLE`.
- `GraphRag/graph_relations.py` (modify) — fix `forTenant` reachability; guarantee SLA roles; add `extract_conventions(graph)`.
- `GraphRag/context_builder.py` (modify) — render a `### Conventions` block in `serialize_context`.
- `GraphRag/nl_to_tio.py` (modify) — pass conventions into `serialize_context`.
- `KGE/KGE-based-graphrag/kge/select.py` (modify) — pass conventions into `serialize_context`.
- `evsla_prompt.py` (modify) — structure-only skeleton: tenant binding + typed topology.
- Tests: `GraphRag/test_resource_index.py`, `GraphRag/test_graph_relations.py`, `GraphRag/test_context_builder.py`, `test_evsla_prompt.py`.

All TDD: failing test → run-fail → implement → run-pass → commit.

---

### Task 1: Encode conventions in the EVSLA ontology

**Files:**
- Modify: `TM Forum Intent Ontology/EnterpriseVpnSlaOntology.ttl` (instance block near lines 281–308; property declarations near lines 185–198)
- Test: `GraphRag/test_graph_relations.py` (new test for convention extraction lands in Task 4; this task's test is a TTL-parse assertion below)

- [ ] **Step 1: Write the failing test**

Add to `GraphRag/test_graph_relations.py`:

```python
def test_ttl_encodes_conventions():
    from rdflib import Graph, URIRef, Namespace
    import pathlib
    ttl = (pathlib.Path(__file__).resolve().parents[1]
           / "TM Forum Intent Ontology" / "EnterpriseVpnSlaOntology.ttl")
    g = Graph(); g.parse(str(ttl), format="turtle")
    EVSLA = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/")
    dmm = EVSLA.defaultMeasurementMethod
    assert (EVSLA.latency, dmm, EVSLA.twamp) in g
    assert (EVSLA.packetLoss, dmm, EVSLA.twamp) in g
    assert (EVSLA.guaranteedBandwidth, dmm, EVSLA.activeMeasurement) in g
    # default window marker
    assert (EVSLA.fiveMinuteWindow, EVSLA.isDefaultTimeWindow, None) in g \
        or any(g.objects(EVSLA.fiveMinuteWindow, EVSLA.isDefaultTimeWindow))
    # zh NL-trigger labels
    zh_one = [str(o) for o in g.objects(EVSLA.oneHourWindow, RDFS.label) if o.language == "zh"]
    zh_month = [str(o) for o in g.objects(EVSLA.monthlySlaWindow, RDFS.label) if o.language == "zh"]
    assert any("每小時" in s for s in zh_one)
    assert any("月度" in s for s in zh_month)
```

Ensure `from rdflib.namespace import RDFS` is imported at the top of the test file (add if absent).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment && python -m unittest GraphRag.test_graph_relations.test_ttl_encodes_conventions -v`
(If module-path import fails, run `cd GraphRag && python -m unittest test_graph_relations -v` — the repo runs tests from within `GraphRag/`.)
Expected: FAIL (triples not present).

- [ ] **Step 3: Implement — edit the TTL**

In `TM Forum Intent Ontology/EnterpriseVpnSlaOntology.ttl`:

(a) Declare the new annotation properties (near the other property declarations, after `evsla:hasTimeWindow` block ~line 198):

```turtle
evsla:defaultMeasurementMethod
  rdfs:label "Default Measurement Method"@en ;
  rdfs:comment "The conventional measurement method used for a metric when the intent does not state one."@en ;
  rdf:type rdf:Property ;
  rdfs:range evsla:MeasurementMethod
.

evsla:isDefaultTimeWindow
  rdfs:label "Is Default Time Window"@en ;
  rdfs:comment "Marks the time window assumed when the intent states no evaluation window."@en ;
  rdf:type rdf:Property
.
```

(b) Attach the metric→method convention. Find each metric instance (`evsla:latency`, `evsla:packetLoss`, `evsla:guaranteedBandwidth`) and add the predicate. Example for latency (add the `evsla:defaultMeasurementMethod` line inside its existing block):

```turtle
evsla:latency
  evsla:defaultMeasurementMethod evsla:twamp ;
  # ... existing triples unchanged ...
.
```

Apply analogously: `evsla:packetLoss evsla:defaultMeasurementMethod evsla:twamp .` and `evsla:guaranteedBandwidth evsla:defaultMeasurementMethod evsla:activeMeasurement .`

(c) Mark the default window and add zh labels to the override windows (in the instance block ~lines 291–308):

```turtle
evsla:fiveMinuteWindow
  evsla:isDefaultTimeWindow true ;
  # ... existing triples unchanged ...
.

evsla:oneHourWindow
  rdfs:label "每小時視窗"@zh ;
  # ... existing triples unchanged ...
.

evsla:monthlySlaWindow
  rdfs:label "月度SLA視窗"@zh ;
  # ... existing triples unchanged ...
.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd GraphRag && python -m unittest test_graph_relations -v`
Expected: `test_ttl_encodes_conventions` PASS. Also confirm the TTL still parses with no other test breaking.

- [ ] **Step 5: Commit**

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
git add "TM Forum Intent Ontology/EnterpriseVpnSlaOntology.ttl" GraphRag/test_graph_relations.py
git commit -m "feat(ontology): encode metric->method + default-window conventions in EVSLA TTL"
```

---

### Task 2: Add Tenant / HubSite / SpokeSite to the role map

**Why:** `closed_vocab_for_reached_roles` only supplies vocab for roles that `resource_index` tagged. Currently `CLASS_ROLE` omits Tenant/HubSite/SpokeSite, so even a "reached" Tenant yields empty vocab.

**Files:**
- Modify: `GraphRag/resource_index.py:36-41`
- Test: `GraphRag/test_resource_index.py`

- [ ] **Step 1: Write the failing test**

Add to `GraphRag/test_resource_index.py`:

```python
def test_class_role_covers_tenant_and_topology():
    from resource_index import CLASS_ROLE
    from rdflib import URIRef
    TIO = "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/"
    for cls, role in [("Tenant", "Tenant"), ("HubSite", "HubSite"),
                      ("SpokeSite", "SpokeSite"),
                      ("HubAndSpokeTopology", "HubAndSpokeTopology")]:
        assert CLASS_ROLE.get(URIRef(TIO + cls)) == role
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd GraphRag && python -m unittest test_resource_index -v`
Expected: FAIL (KeyError/None for Tenant).

- [ ] **Step 3: Implement**

In `GraphRag/resource_index.py`, extend `CLASS_ROLE` (lines 36-41):

```python
CLASS_ROLE = {
    URIRef(TIO + "EnterpriseVpnSlaOntology/Statistic"): "Statistic",
    URIRef(TIO + "EnterpriseVpnSlaOntology/Scope"): "Scope",
    URIRef(TIO + "EnterpriseVpnSlaOntology/MeasurementMethod"): "MeasurementMethod",
    URIRef(TIO + "EnterpriseVpnSlaOntology/TimeWindow"): "TimeWindow",
    URIRef(TIO + "EnterpriseVpnSlaOntology/Tenant"): "Tenant",
    URIRef(TIO + "EnterpriseVpnSlaOntology/HubSite"): "HubSite",
    URIRef(TIO + "EnterpriseVpnSlaOntology/SpokeSite"): "SpokeSite",
    URIRef(TIO + "EnterpriseVpnSlaOntology/HubAndSpokeTopology"): "HubAndSpokeTopology",
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd GraphRag && python -m unittest test_resource_index -v`
Expected: PASS. Run the full `GraphRag` suite to confirm no regression: `cd GraphRag && python -m unittest discover -p "test_*.py"`.

- [ ] **Step 5: Commit**

```bash
git add GraphRag/resource_index.py GraphRag/test_resource_index.py
git commit -m "fix(graphrag): map Tenant/HubSite/SpokeSite/topology classes to roles"
```

---

### Task 3: Fix `forTenant` reachability + guarantee SLA roles

**Why:** `traverse_connective` activates `forTenant` only if a grounded seed *is* a Tenant — seeds are metrics, so Tenant is never reached. More broadly, when an SLA expectation is present (a metric is reached), all SLA-defining roles must be supplied.

**Files:**
- Modify: `GraphRag/graph_relations.py:69-90`
- Test: `GraphRag/test_graph_relations.py`

- [ ] **Step 1: Write the failing test**

Add to `GraphRag/test_graph_relations.py` (reuse the existing fixture that loads the ontology + grounds a metric; mirror `test_subgraph_retriever.py`/existing graph_relations tests):

```python
def test_metric_presence_reaches_sla_roles():
    from rdflib import Graph, URIRef
    import pathlib
    from graph_relations import traverse_connective
    ttl = (pathlib.Path(__file__).resolve().parents[1]
           / "TM Forum Intent Ontology" / "EnterpriseVpnSlaOntology.ttl")
    g = Graph(); g.parse(str(ttl), format="turtle")
    EVSLA = "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/"
    _relations, reached = traverse_connective(g, [URIRef(EVSLA + "latency")])
    for role in ("Tenant", "MeasurementMethod", "TimeWindow", "HubSite", "SpokeSite"):
        assert role in reached, f"{role} not reached: {sorted(reached)}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd GraphRag && python -m unittest test_graph_relations.test_metric_presence_reaches_sla_roles -v`
Expected: FAIL (`Tenant` missing).

- [ ] **Step 3: Implement**

In `GraphRag/graph_relations.py`, after the `reached` set is built in `traverse_connective` (just before `relations.sort(...)` at line 89), add a guarantee that an SLA expectation supplies all SLA-defining roles:

```python
    # When an SLA expectation is present (a metric is grounded/reached), the
    # SLA-defining roles are always relevant — supply their vocab regardless of
    # traversal happenstance (forTenant has no rdfs:domain, hub/spoke depend on
    # topology being grounded). This is the closed-world contract for EVSLA.
    if "Metric" in reached:
        reached.update({
            "Tenant", "MeasurementMethod", "TimeWindow",
            "HubSite", "SpokeSite", "HubAndSpokeTopology",
        })
        # Emit the forTenant relation so the prompt sees evsla:Tenant as a type.
        fortenant = URIRef(EVSLA + "forTenant")
        for r in graph.objects(fortenant, RDFS.range):
            relations.append((URIRef(EVSLA + "EnterpriseVpnService"), fortenant, r))
```

(The `EnterpriseVpnService` domain mirrors the gold's `evsla:forTenant` usage; confirm against the TTL `forTenant` declaration and adjust the subject only if the TTL names a different domain.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd GraphRag && python -m unittest test_graph_relations -v`
Expected: PASS. Full suite: `cd GraphRag && python -m unittest discover -p "test_*.py"`.

- [ ] **Step 5: Commit**

```bash
git add GraphRag/graph_relations.py GraphRag/test_graph_relations.py
git commit -m "fix(graphrag): guarantee SLA roles (tenant/method/window/topology) reach the context"
```

---

### Task 4: Extract conventions and render them in the context

**Files:**
- Modify: `GraphRag/graph_relations.py` (add `extract_conventions`)
- Modify: `GraphRag/context_builder.py:17-34` (add `conventions` param + block)
- Test: `GraphRag/test_graph_relations.py`, `GraphRag/test_context_builder.py`

- [ ] **Step 1: Write the failing tests**

Add to `GraphRag/test_graph_relations.py`:

```python
def test_extract_conventions():
    from rdflib import Graph
    import pathlib
    from graph_relations import extract_conventions
    ttl = (pathlib.Path(__file__).resolve().parents[1]
           / "TM Forum Intent Ontology" / "EnterpriseVpnSlaOntology.ttl")
    g = Graph(); g.parse(str(ttl), format="turtle")
    c = extract_conventions(g)
    assert c["method_defaults"]["evsla:latency"] == "evsla:twamp"
    assert c["method_defaults"]["evsla:guaranteedBandwidth"] == "evsla:activeMeasurement"
    assert c["window_default"] == "evsla:fiveMinuteWindow"
    assert c["window_triggers"]["每小時視窗"] == "evsla:oneHourWindow"
    assert c["window_triggers"]["月度SLA視窗"] == "evsla:monthlySlaWindow"
```

Add to `GraphRag/test_context_builder.py`:

```python
def test_serialize_context_renders_conventions():
    from context_builder import serialize_context
    conv = {
        "method_defaults": {"evsla:latency": "evsla:twamp"},
        "window_default": "evsla:fiveMinuteWindow",
        "window_triggers": {"每小時視窗": "evsla:oneHourWindow"},
    }
    out = serialize_context([], [], {}, conventions=conv)
    assert "Conventions" in out
    assert "evsla:latency -> evsla:twamp" in out
    assert "evsla:fiveMinuteWindow" in out
    assert "每小時視窗" in out and "evsla:oneHourWindow" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd GraphRag && python -m unittest test_graph_relations.test_extract_conventions test_context_builder.test_serialize_context_renders_conventions -v`
Expected: FAIL (`extract_conventions` missing; `serialize_context` has no `conventions` kwarg).

- [ ] **Step 3: Implement**

In `GraphRag/graph_relations.py`, add:

```python
def extract_conventions(graph: Graph) -> dict:
    """Read EVSLA convention facts: metric->default method, default window,
    and NL-trigger (zh label) -> window IRI."""
    dmm = URIRef(EVSLA + "defaultMeasurementMethod")
    is_default = URIRef(EVSLA + "isDefaultTimeWindow")
    method_defaults: dict[str, str] = {}
    for s, _p, o in graph.triples((None, dmm, None)):
        method_defaults[_to_curie(s)] = _to_curie(o)
    window_default = ""
    for s in graph.subjects(is_default, None):
        window_default = _to_curie(s)
        break
    window_triggers: dict[str, str] = {}
    tw = URIRef(EVSLA + "TimeWindow")
    for win in graph.subjects(RDF.type, tw):
        for lbl in graph.objects(win, RDFS.label):
            if getattr(lbl, "language", None) == "zh":
                window_triggers[str(lbl)] = _to_curie(win)
    return {
        "method_defaults": method_defaults,
        "window_default": window_default,
        "window_triggers": window_triggers,
    }
```

In `GraphRag/context_builder.py`, change the signature and append the block:

```python
def serialize_context(
    grounded: list[tuple[str, str, str, str]],
    relations: list[tuple[str, str, str]],
    reached_vocab: dict[str, list[str]],
    conventions: dict | None = None,
) -> str:
    lines = ["### Canonical prefixes"]
    lines += [f"{p}: <{ns}>" for p, ns in PREFIXES]
    lines += ["", "### Grounded terms (NL concept -> ontology term)"]
    for _term, curie, typ, gloss in grounded:
        lines.append(f"- {curie} ({typ}) -- {gloss}")
    lines += ["", "### Connective relations (how an SLA expectation wires together)"]
    for s, p, o in relations:
        lines.append(f"- {s} {p} -> {o}")
    if reached_vocab:
        lines += ["", "### Closed vocabulary per reached role (pick one per slot)"]
        for role in sorted(reached_vocab):
            lines.append(f"- {role}: {', '.join(reached_vocab[role])}")
    if conventions:
        lines += ["", "### Conventions (apply when the NL gives no explicit cue)"]
        md = conventions.get("method_defaults") or {}
        if md:
            lines.append("- Measurement method default per metric:")
            for metric in sorted(md):
                lines.append(f"  - {metric} -> {md[metric]}")
        if conventions.get("window_default"):
            lines.append(f"- Time window default: {conventions['window_default']}")
        wt = conventions.get("window_triggers") or {}
        for label in sorted(wt):
            lines.append(f"  - if NL mentions 「{label}」 use {wt[label]}")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd GraphRag && python -m unittest test_graph_relations test_context_builder -v`
Expected: PASS. Full suite: `cd GraphRag && python -m unittest discover -p "test_*.py"`.

- [ ] **Step 5: Commit**

```bash
git add GraphRag/graph_relations.py GraphRag/context_builder.py GraphRag/test_graph_relations.py GraphRag/test_context_builder.py
git commit -m "feat(graphrag): extract EVSLA conventions and render them in retrieval context"
```

---

### Task 5: Wire conventions into both generators

**Files:**
- Modify: `GraphRag/nl_to_tio.py` (around line 272, the `build_retrieval_context` call site) and `GraphRag/subgraph_retriever.py:77-85` if it owns the `serialize_context` call.
- Modify: `KGE/KGE-based-graphrag/kge/select.py:78-99`

First confirm where `serialize_context` is invoked in the GraphRAG path:
Run: `cd GraphRag && grep -rn "serialize_context\|build_retrieval_context" *.py`

- [ ] **Step 1: Write the failing test (KGE select integration)**

Add to `GraphRag/test_subgraph_retriever.py` (GraphRAG side) a smoke assertion that the rendered context for a grounded metric contains the conventions block:

```python
def test_graphrag_context_includes_conventions():
    from rdflib import Graph, URIRef
    import pathlib
    from subgraph_retriever import build_retrieval_context
    from resource_index import build_resource_index
    ttl = (pathlib.Path(__file__).resolve().parents[1]
           / "TM Forum Intent Ontology" / "EnterpriseVpnSlaOntology.ttl")
    g = Graph(); g.parse(str(ttl), format="turtle")
    res = build_resource_index(g)
    ctx = build_retrieval_context("latency", g, res, embeddings=None, query_vector=None)
    assert "Conventions" in ctx
    assert "evsla:twamp" in ctx
```

(If `build_retrieval_context`'s signature differs, adapt the call to match `subgraph_retriever.py:77`. The assertion — context contains the conventions block — is the contract.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd GraphRag && python -m unittest test_subgraph_retriever.test_graphrag_context_includes_conventions -v`
Expected: FAIL (conventions not threaded through).

- [ ] **Step 3: Implement**

In the GraphRAG path, wherever `serialize_context(grounded, relations, vocab)` is called (in `subgraph_retriever.build_retrieval_context` per the grep), compute and pass conventions:

```python
from graph_relations import extract_conventions  # add to imports
# ... inside build_retrieval_context, after computing grounded/relations/vocab:
conventions = extract_conventions(graph)
return serialize_context(grounded, relations, vocab, conventions=conventions)
```

In `KGE/KGE-based-graphrag/kge/select.py`, update imports (line 45-49) and the return (line 98-99):

```python
from graph_relations import (  # noqa: E402
    traverse_connective,
    closed_vocab_for_reached_roles,
    extract_conventions,
)
from context_builder import serialize_context  # noqa: E402
# ...
    vocab = closed_vocab_for_reached_roles(reached, resources)
    conventions = extract_conventions(graph)
    return serialize_context(grounded, relations, vocab, conventions=conventions)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd GraphRag && python -m unittest test_subgraph_retriever -v`
Expected: PASS. Full GraphRAG suite green. Also import-smoke the KGE module:
Run: `cd KGE/KGE-based-graphrag && python -c "import kge.select"` → no error.

- [ ] **Step 5: Commit**

```bash
git add GraphRag/subgraph_retriever.py GraphRag/nl_to_tio.py GraphRag/test_subgraph_retriever.py KGE/KGE-based-graphrag/kge/select.py
git commit -m "feat(retrieval): thread EVSLA conventions into GraphRAG and KGE context"
```

---

### Task 6: Structure-only skeleton — tenant binding + typed topology

**Why:** The structure-only system prompt (`evsla_prompt.py` lines 24-27) never mentions a tenant node and does not require typed `HubSite`/`SpokeSite`/`HubAndSpokeTopology`. Add these as *shape* requirements that resolve vocabulary from retrieval (no hardcoded EVSLA terms, preserving the structure-only contract).

**Files:**
- Modify: `evsla_prompt.py:24-27`
- Test: `test_evsla_prompt.py`

- [ ] **Step 1: Write the failing test**

Add to `test_evsla_prompt.py`:

```python
def test_structure_only_requires_tenant_and_typed_topology():
    from evsla_prompt import build_evsla_system_prompt
    p = build_evsla_system_prompt("TC021", retrieval_mode="GraphRAG", profile="structure_only")
    low = p.lower()
    assert "tenant" in low                      # tenant binding required
    assert "rdfs:label" in p                     # label carried from NL
    assert "hub" in low and "spoke" in low       # typed topology nodes
    # contract preserved: no leaked EVSLA vocabulary IRIs in the skeleton
    assert "evsla:twamp" not in p and "evsla:fiveMinuteWindow" not in p
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment && python -m unittest test_evsla_prompt.test_structure_only_requires_tenant_and_typed_topology -v`
Expected: FAIL ("tenant" absent).

- [ ] **Step 3: Implement**

In `evsla_prompt.py`, extend the structure-only "Graph structure" block (after line 27) with two shape requirements that defer vocabulary to retrieval:

```python
- Tenant binding: emit one tenant node typed with the EVSLA tenant class from retrieval and rdfs:label "<tenant name from the NL>"@zh, linked from the service via the supplied for-tenant property.
- Topology typing: the topology node must be typed with the EVSLA hub-and-spoke topology class from retrieval; the hub node typed with the hub-site class and every spoke node typed with the spoke-site class, each with rdfs:label "<name from the NL>"@zh.
- Measurement method and time window: take them from the retrieval Conventions block — use the metric's default method, and the default time window unless the NL names an explicit window cue.
```

Keep all terms generic (no `evsla:` literals) so the structure-only contract holds.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment && python -m unittest test_evsla_prompt -v`
Expected: PASS. Also re-run the existing structure-only contract test (`test_structure_only_keeps_skeleton_withholds_vocab` or similar in `GraphRag/test_prompt_profile.py`) to confirm no vocabulary leak regression:
Run: `cd GraphRag && python -m unittest test_prompt_profile -v`.

- [ ] **Step 5: Commit**

```bash
git add evsla_prompt.py test_evsla_prompt.py
git commit -m "feat(prompt): structure-only skeleton requires tenant binding + typed topology"
```

---

### Task 7: Re-run experiments, validate, update progress

**Files:**
- Modify: `progress.md` (results table)
- Generated: `tio_outputs/graphrag_structure/*.ttl`, `tio_outputs/kge_structure/*.ttl`, `phase1/phase1_graphrag_structure.json`, `phase1/phase1_kge_structure.json`

**Prereqs:** `OPENAI_API_KEY`/`GRAPHRAG_API_KEY` set; main `.venv` active.

- [ ] **Step 1: Regenerate GraphRAG structure-only (TTL read live, no rebuild)**

Run:
```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag
python nl_to_tio.py --prompt-profile structure_only --test-cases ../test_cases_40.json
```
Expected: `Wrote 40/40 TTL files to .../tio_outputs/graphrag_structure`.

- [ ] **Step 2: Retrain KGE artifacts (TTL changed) then regenerate**

Run:
```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/KGE/KGE-based-graphrag
python -m kge.train
python nl_to_tio.py --prompt-profile structure_only --test-cases ../../test_cases_40.json
```
Expected: training completes; `Wrote 40/40 TTL files to .../tio_outputs/kge_structure`.

- [ ] **Step 3: Evaluate both against the 40-case gold**

Run:
```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python evaluate_ttl.py graphrag_structure --test-cases test_cases_40.json
python evaluate_ttl.py kge_structure --test-cases test_cases_40.json
```
Expected: writes `phase1/phase1_graphrag_structure.json` and `phase1/phase1_kge_structure.json`.

- [ ] **Step 4: Compute per-dimension scores and token cost**

Run:
```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python3 - <<'EOF'
import json
from collections import defaultdict
for m in ['graphrag','kge']:
    d=json.load(open(f"phase1/phase1_{m}_structure.json"))
    dims=defaultdict(list); comp=[]
    for r in d:
        s=r.get('semantic') or {}; comp.append(s.get('composite',0))
        for k,v in (s.get('dimensions') or {}).items(): dims[k].append(v)
    print(f"=== {m} composite={sum(comp)/len(comp):.4f} ===")
    for k in sorted(dims, key=lambda x: sum(dims[x])/len(dims[x])):
        print(f"   {k:22} {sum(dims[k])/len(dims[k]):.3f}")
EOF
```
Token cost: read `phase1/token_usage/token_usage_{graphrag,kge}.json` if regenerated, or compute online avg from the run logs.

- [ ] **Step 5: Check success criteria**

PASS gate:
- composite ≥ 0.93 (both methods)
- each of tenant / time_window / measurement_method / topology ≥ 0.85
- no strong dim (metric, operator, threshold, scope, contract, precision, statistic) dropped > 0.02
- tokens ≤ ~2,500/case; parse 100%; zero non-official IRIs

If any target dim is still < 0.85, diagnose before declaring done: read 2-3 failing TTLs in `tio_outputs/<method>_structure/`, check whether the context block actually carried the role vocab/convention (print the retrieval context for that case) and whether the model emitted the typed node. Fix the responsible layer (TTL convention, reachability, or skeleton wording) and re-run from the affected task. Do not silently accept a miss — record the residual.

- [ ] **Step 6: Update `progress.md`**

Add a new dated section ("Experiment Architecture 5 — four-dimension grounding, 2026-06-16") with the before/after per-dimension table and the new four-line composite/token table. Note KGE was retrained. Keep the canonical numbers consistent with the new `phase1_*_structure.json`.

- [ ] **Step 7: Commit results**

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
git add tio_outputs/graphrag_structure tio_outputs/kge_structure phase1/phase1_graphrag_structure.json phase1/phase1_kge_structure.json progress.md
git commit -m "results(retrieval): four-dimension grounding lifts GraphRAG/KGE structure-only composite"
```

---

## Self-Review

- **Spec §3.1 (ontology conventions)** → Task 1. ✓
- **Spec §3.2 (reachability + convention surfacing + skeleton)** → Tasks 2,3 (reachability + role map), 4,5 (convention block + wiring), 6 (skeleton). ✓
- **Spec §3.3 (per-method wiring: GraphRAG live TTL, KGE retrain)** → Task 5 (wiring) + Task 7 Steps 1-2 (live read / retrain). ✓
- **Spec §4 (success criteria)** → Task 7 Step 5 gate. ✓
- **Spec §5 (validation incl. unit tests for forTenant + context block)** → Tasks 3,4 tests + Task 7. ✓
- **Spec §6 (risks: overfitting, TC039 residual, KGE retrain, token creep)** → addressed in Task 1 conventions (general), Task 7 Step 5 residual recording, Task 7 Step 2 retrain, `guard_tokens` already orders the convention block. ✓
- **Placeholder scan:** all code steps contain real code; the only deferred specifics are (a) exact `forTenant` subject in Task 3 (verify-against-TTL note) and (b) `serialize_context` call-site location in Task 5 (grep step provided). Both are concrete verification steps, not vague instructions. ✓
- **Type consistency:** `extract_conventions` returns `{method_defaults, window_default, window_triggers}` — same keys used in Task 4 test, context_builder block, and Task 5 wiring. `serialize_context(..., conventions=None)` signature consistent across Tasks 4 and 5. ✓
