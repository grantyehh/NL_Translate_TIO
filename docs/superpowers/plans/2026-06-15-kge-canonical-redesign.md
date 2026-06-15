# KGE Canonical Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the KGE line's misused retrieval (TransE entity-cosine expansion, predicted-triples-as-facts dump, encyclopedic term dump) with a canonical pipeline — text-embedding dense grounding + TransE link-prediction over **real** triples only — that emits the **same** output contract as the redesigned GraphRAG, so the comparison isolates the term-selection mechanism.

**Architecture:** A new `kge/select.py` does: text-embedding entry grounding (cosine over entity text embeddings) → TransE-ranked expansion constrained to triples that exist in `triples.tsv` → feeds the grounded URI set into GraphRAG's shared output-contract modules (`resource_index`, `graph_relations`, `context_builder`). `kge/retrieve.py` loses the three misuse functions but keeps its artifact loaders. `nl_to_tio.py` swaps one call. `train.py` and the trained artifacts are untouched.

**Tech Stack:** Python 3, numpy, rdflib, OpenAI SDK (embeddings), pytest. Reuses `GraphRag/{ontology_graph,resource_index,graph_relations,context_builder}.py`. Artifacts in `KGE/KGE-based-graphrag/kge_data/`. Spec: `docs/superpowers/specs/2026-06-15-kge-canonical-redesign-design.md`.

---

## File Structure

- `KGE/KGE-based-graphrag/kge/select.py` (new) — the canonical selection pipeline: `text_ground`, `transe_expand`, `assemble_context`, `build_kge_context`. One responsibility: turn an NL query into the shared retrieval-context string using embeddings soundly.
- `KGE/KGE-based-graphrag/kge/test_select.py` (new) — offline tests for `transe_expand`, `assemble_context`, `build_kge_context` (text_ground monkeypatched).
- `KGE/KGE-based-graphrag/kge/retrieve.py` (modify) — remove the misuse functions; keep loaders/helpers `select.py` reuses.
- `KGE/KGE-based-graphrag/kge/test_retrieve_cleanup.py` (new) — asserts the misuse functions are gone and the loaders remain.
- `KGE/KGE-based-graphrag/nl_to_tio.py` (modify) — swap the retrieval call to `select.build_kge_context`.

All paths come from `kge.paths` (`PROJECT_ROOT` = repo root, `ONTOLOGY_DIR`, `ENTITY_IDS_JSON`, `TRIPLES_TSV`, `MANIFEST_JSON`).

Run all tests with the repo venv: `.venv/bin/python -m pytest <path> -v` from the repo root `/Users/grantyeh/Grant/Project/CHT/TIO_Experiment`. (numpy, rdflib, openai, pytest are installed.)

---

## Task 1: `transe_expand` — rank REAL triples only

**Files:**
- Create: `KGE/KGE-based-graphrag/kge/select.py` (first function)
- Test: `KGE/KGE-based-graphrag/kge/test_select.py`

- [ ] **Step 1: Write the failing test**

```python
# KGE/KGE-based-graphrag/kge/test_select.py
import json
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent           # KGE/KGE-based-graphrag
sys.path.insert(0, str(EXP))
from kge.paths import ENTITY_IDS_JSON, TRIPLES_TSV, PROJECT_ROOT
from kge import select

TIO = "http://tio.models.tmforum.org/tio/v3.6.0/"
LATENCY = TIO + "EnterpriseVpnSlaOntology/latency"

def _real_triples():
    rows = []
    for line in TRIPLES_TSV.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            rows.append(tuple(parts))
    return rows

def test_transe_expand_returns_only_real_entities():
    out = select.transe_expand([LATENCY], top_k=8)
    eids = set(json.load(open(ENTITY_IDS_JSON, encoding="utf-8")))
    assert out, "expected some expansion for a seed that occurs in triples"
    assert all(u in eids for u in out)                 # never fabricated entities
    rows = _real_triples()
    mates = {h for h, r, t in rows if t == LATENCY} | {t for h, r, t in rows if h == LATENCY}
    assert set(out) <= mates                           # every result co-occurs in a REAL triple with the seed
    assert LATENCY not in out                           # seed itself excluded

def test_transe_expand_empty_for_unknown_seed():
    assert select.transe_expand(["http://example.org/not-an-entity"], top_k=8) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest KGE/KGE-based-graphrag/kge/test_select.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kge.select'`.

- [ ] **Step 3: Write minimal implementation**

```python
# KGE/KGE-based-graphrag/kge/select.py
from __future__ import annotations

import sys

from kge.paths import PROJECT_ROOT
from kge.retrieve import (
    _load_kge_link_arrays,
    _load_triple_rows,
    kge_link_prediction_ready,
    trans_e_score,
)

# Reuse GraphRAG's shared output-contract modules (spec §6).
sys.path.insert(0, str(PROJECT_ROOT / "GraphRag"))


def transe_expand(seed_uris: list[str], *, top_k: int = 8) -> list[str]:
    """Expand seeds to related entities by ranking the REAL triples that contain
    a seed (TransE plausibility -‖h+r−t‖). Returns entities from those real
    triples only — never fabricates a triple or an entity."""
    if not seed_uris or not kge_link_prediction_ready():
        return []
    entity_ids, relation_ids, entity_kge, relation_kge = _load_kge_link_arrays()
    eidx = {u: i for i, u in enumerate(entity_ids)}
    ridx = {u: i for i, u in enumerate(relation_ids)}
    seeds = set(seed_uris)
    scored: list[tuple[float, str, str]] = []
    for h, r, t in _load_triple_rows():
        if (h in seeds or t in seeds) and h in eidx and r in ridx and t in eidx:
            s = trans_e_score(entity_kge[eidx[h]], relation_kge[ridx[r]], entity_kge[eidx[t]])
            scored.append((s, h, t))
    scored.sort(key=lambda x: (-x[0], x[1], x[2]))
    out: list[str] = []
    for _s, h, t in scored[:top_k]:
        for e in (h, t):
            if e not in seeds and e not in out:
                out.append(e)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest KGE/KGE-based-graphrag/kge/test_select.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add KGE/KGE-based-graphrag/kge/select.py KGE/KGE-based-graphrag/kge/test_select.py
git commit -m "feat(kge): transe_expand ranks real triples only (no synthesis)"
```

---

## Task 2: `assemble_context` — shared output contract from grounded URIs

**Files:**
- Modify: `KGE/KGE-based-graphrag/kge/select.py`
- Test: `KGE/KGE-based-graphrag/kge/test_select.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to KGE/KGE-based-graphrag/kge/test_select.py
def test_assemble_context_clean_and_scoped():
    ctx = select.assemble_context([LATENCY])
    # self-contained, shared GraphRAG contract
    assert "### Canonical prefixes" in ctx
    assert "evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/>" in ctx
    assert "evsla:latency" in ctx
    # grounding a metric activates the SlaExpectation hub -> SLA roles appear
    assert "Statistic:" in ctx and "Scope:" in ctx
    # NONE of the old misuse artifacts
    assert "TransE score=" not in ctx
    assert "Predicted likely triples" not in ctx
    # no schema plumbing fact lines
    for bad in (" rdfs:subClassOf ", " rdfs:domain ", " rdfs:range "):
        assert bad not in ctx
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest KGE/KGE-based-graphrag/kge/test_select.py -k assemble -v`
Expected: FAIL — `select` has no `assemble_context`.

- [ ] **Step 3: Write minimal implementation**

Append to `KGE/KGE-based-graphrag/kge/select.py` (the GraphRAG imports must come after the `sys.path.insert` already added in Task 1):

```python
from rdflib import URIRef  # noqa: E402

from ontology_graph import load_ontology  # noqa: E402
from resource_index import build_resource_index, to_curie  # noqa: E402
from graph_relations import (  # noqa: E402
    traverse_connective,
    closed_vocab_for_reached_roles,
)
from context_builder import serialize_context  # noqa: E402
from kge.paths import ONTOLOGY_DIR  # noqa: E402

_GRAPH = None
_RESOURCES = None


def _ontology():
    """Load + index the ontology once (cached); avoids re-parsing per case."""
    global _GRAPH, _RESOURCES
    if _GRAPH is None:
        _GRAPH = load_ontology(ONTOLOGY_DIR)
        _RESOURCES = build_resource_index(_GRAPH)
    return _GRAPH, _RESOURCES


def assemble_context(grounded_uris: list[str]) -> str:
    """Turn an embedding-selected grounded URI set into the SHARED GraphRAG
    output contract (@prefix + grounded terms + connective relations + closed
    vocab). Mirrors GraphRag.subgraph_retriever.build_retrieval_context, but the
    seeds come from KGE selection rather than lexical/deterministic grounding."""
    graph, resources = _ontology()
    by_uri = {r.uri: r for r in resources}
    seen: list[str] = []
    for u in grounded_uris:
        if u not in seen:
            seen.append(u)
    grounded_uris = seen

    relations_raw, reached = traverse_connective(graph, [URIRef(u) for u in grounded_uris])
    for u in grounded_uris:
        r = by_uri.get(u)
        if r and r.role_class:
            reached.add(r.role_class)

    relations = [
        (to_curie(str(s)), to_curie(str(p)), to_curie(str(o)))
        for s, p, o in relations_raw
    ]
    grounded = [
        (
            (by_uri[u].labels[0] if by_uri[u].labels else by_uri[u].curie),
            by_uri[u].curie,
            "; ".join(by_uri[u].rdf_types) or "resource",
            by_uri[u].comment[:160],
        )
        for u in grounded_uris
        if u in by_uri and by_uri[u].role_class is not None
    ]
    vocab = closed_vocab_for_reached_roles(reached, resources)
    return serialize_context(grounded, relations, vocab)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest KGE/KGE-based-graphrag/kge/test_select.py -v`
Expected: PASS (all three tests).

- [ ] **Step 5: Commit**

```bash
git add KGE/KGE-based-graphrag/kge/select.py KGE/KGE-based-graphrag/kge/test_select.py
git commit -m "feat(kge): assemble_context reuses GraphRAG shared output contract"
```

---

## Task 3: `text_ground` + `build_kge_context` — entry grounding + orchestration

**Files:**
- Modify: `KGE/KGE-based-graphrag/kge/select.py`
- Test: `KGE/KGE-based-graphrag/kge/test_select.py` (append)

- [ ] **Step 1: Write the failing test** (offline — monkeypatches the API-dependent `text_ground`)

```python
# append to KGE/KGE-based-graphrag/kge/test_select.py
def test_build_kge_context_wires_grounding(monkeypatch):
    monkeypatch.setattr(select, "text_ground", lambda q, **k: [LATENCY])
    ctx = select.build_kge_context("延遲低於50ms")
    assert "### Canonical prefixes" in ctx
    assert "evsla:latency" in ctx
    assert "TransE score=" not in ctx and "Predicted likely triples" not in ctx

def test_text_ground_callable_exists():
    assert callable(select.text_ground)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest KGE/KGE-based-graphrag/kge/test_select.py -k "wires or text_ground_callable" -v`
Expected: FAIL — `select` has no `text_ground` / `build_kge_context`.

- [ ] **Step 3: Write minimal implementation**

Append to `KGE/KGE-based-graphrag/kge/select.py`:

```python
import json  # noqa: E402
import os  # noqa: E402

import numpy as np  # noqa: E402

from kge.retrieve import _load_arrays, _embed_query, kge_ready  # noqa: E402
from kge.paths import MANIFEST_JSON  # noqa: E402

TEXT_TOP_K = 8
EXPAND_TOP_K = 8


def _resolve_embedding_model() -> str:
    if MANIFEST_JSON.is_file():
        m = json.loads(MANIFEST_JSON.read_text(encoding="utf-8")).get("text_embedding_model")
        if m:
            return m
    return "text-embedding-3-small"


def text_ground(query: str, *, top_k: int = TEXT_TOP_K, case_id: str | None = None) -> list[str]:
    """Dense entity retrieval: cosine(query text embedding, entity text
    embeddings) -> top-k entity URIs. Catches non-lexical / synonym mentions."""
    if not kge_ready():
        return []
    api_key = os.getenv("GRAPHRAG_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []
    entity_ids, _kge, text_emb = _load_arrays()
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    prev = os.getenv("KGE_ACTIVE_CASE_ID")
    if case_id:
        os.environ["KGE_ACTIVE_CASE_ID"] = case_id
    try:
        q = _embed_query(client, query, _resolve_embedding_model())
    finally:
        if case_id:
            if prev is None:
                os.environ.pop("KGE_ACTIVE_CASE_ID", None)
            else:
                os.environ["KGE_ACTIVE_CASE_ID"] = prev
    scores = text_emb @ q
    idx = np.argsort(-scores)[:top_k]
    return [entity_ids[i] for i in idx.tolist()]


def build_kge_context(query: str, *, case_id: str | None = None) -> str:
    """Canonical KGE retrieval context: text-embedding grounding + TransE
    real-triple expansion -> shared GraphRAG output contract."""
    seeds = text_ground(query, case_id=case_id)
    expanded = transe_expand(seeds, top_k=EXPAND_TOP_K)
    return assemble_context(seeds + expanded)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest KGE/KGE-based-graphrag/kge/test_select.py -v`
Expected: PASS (all five tests).

- [ ] **Step 5: Commit**

```bash
git add KGE/KGE-based-graphrag/kge/select.py KGE/KGE-based-graphrag/kge/test_select.py
git commit -m "feat(kge): text-embedding grounding + build_kge_context orchestration"
```

---

## Task 4: Remove the misuse functions from `retrieve.py`

**Files:**
- Modify: `KGE/KGE-based-graphrag/kge/retrieve.py`
- Test: `KGE/KGE-based-graphrag/kge/test_retrieve_cleanup.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# KGE/KGE-based-graphrag/kge/test_retrieve_cleanup.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kge import retrieve

def test_misuse_functions_removed():
    for gone in ("predict_likely_triples", "format_grounded_kge_context",
                 "format_kge_context_for_prompt", "get_kge_ranked_entities",
                 "score_link_predictions"):
        assert not hasattr(retrieve, gone), f"{gone} should be removed"

def test_loaders_and_helpers_kept():
    for kept in ("_load_arrays", "_load_kge_link_arrays", "_load_triple_rows",
                 "_embed_query", "trans_e_score", "kge_ready",
                 "kge_link_prediction_ready", "_uri_to_curie"):
        assert hasattr(retrieve, kept), f"{kept} must remain"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest KGE/KGE-based-graphrag/kge/test_retrieve_cleanup.py -v`
Expected: FAIL on `test_misuse_functions_removed` (functions still present).

- [ ] **Step 3: Edit `retrieve.py`**

Delete these functions and any now-unused helper used ONLY by them:
`score_link_predictions`, `_default_relation_whitelist`, `_candidate_tail_uris`,
`predict_likely_triples`, `format_grounded_kge_context`, `get_kge_ranked_entities`,
`format_kge_context_for_prompt`, and `_top_k_indices` and `_artifacts_ready`
(both used only by `get_kge_ranked_entities`). Keep `LinkPrediction` only if it
is still referenced after deletion; otherwise delete it too. Keep the module
imports that remaining functions need (numpy, json, os, OpenAI, paths, etc.).
Do NOT touch the loaders, `kge_ready`, `kge_link_prediction_ready`,
`_embed_query`, `trans_e_score`, `_uri_to_curie`, `TIO_PREFIXES`.

After editing, verify the module still imports:
Run: `.venv/bin/python -c "import sys; sys.path.insert(0,'KGE/KGE-based-graphrag'); from kge import retrieve; print('ok')"`
Expected: `ok` (no NameError from a leftover reference to a deleted helper).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest KGE/KGE-based-graphrag/kge/test_retrieve_cleanup.py KGE/KGE-based-graphrag/kge/test_select.py -v`
Expected: PASS (cleanup tests + the select tests still green, since `select.py` only uses kept helpers).

- [ ] **Step 5: Commit**

```bash
git add KGE/KGE-based-graphrag/kge/retrieve.py KGE/KGE-based-graphrag/kge/test_retrieve_cleanup.py
git commit -m "refactor(kge): remove misused link-prediction dump + cosine expansion"
```

---

## Task 5: Wire `nl_to_tio.py` to the canonical retrieval

**Files:**
- Modify: `KGE/KGE-based-graphrag/nl_to_tio.py`
- Test: `KGE/KGE-based-graphrag/test_structure_profile.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to KGE/KGE-based-graphrag/test_structure_profile.py
def test_nl_to_tio_uses_canonical_kge_retrieval():
    import inspect, nl_to_tio
    src = inspect.getsource(nl_to_tio)
    assert "build_kge_context" in src
    assert "format_kge_context_for_prompt" not in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest "KGE/KGE-based-graphrag/test_structure_profile.py" -k canonical -v`
Expected: FAIL — `nl_to_tio` still references `format_kge_context_for_prompt`.

- [ ] **Step 3: Edit `nl_to_tio.py`**

Change the import on line 10 from:
```python
from kge.retrieve import format_kge_context_for_prompt, kge_ready
```
to:
```python
from kge.retrieve import kge_ready
from kge.select import build_kge_context
```
Then change the per-case retrieval call (currently
`kge_context = format_kge_context_for_prompt(tc["nl_intent"], case_id=tc["id"])`)
to:
```python
        kge_context = build_kge_context(tc["nl_intent"], case_id=tc["id"])
```
Leave everything else (the `--prompt-profile` wiring, `kge_structure` output key,
token recording) unchanged. Confirm import is still side-effect-free:
Run: `.venv/bin/python -c "import sys; sys.path.insert(0,'KGE/KGE-based-graphrag'); sys.path.insert(0,'.'); import nl_to_tio; print('ok')"`
Expected: `ok` with no API key set.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest "KGE/KGE-based-graphrag/" -v`
Expected: PASS (the new test + existing KGE tests).

- [ ] **Step 5: Commit**

```bash
git add "KGE/KGE-based-graphrag/nl_to_tio.py" "KGE/KGE-based-graphrag/test_structure_profile.py"
git commit -m "feat(kge): wire nl_to_tio to canonical build_kge_context"
```

---

## Task 6: Offline gate, then re-run + evaluate `kge_structure`

**Files:** none (verification + run)

- [ ] **Step 1: Offline gate (no API)**

Run:
```bash
.venv/bin/python -m pytest KGE/KGE-based-graphrag/kge/test_select.py \
  KGE/KGE-based-graphrag/kge/test_retrieve_cleanup.py \
  "KGE/KGE-based-graphrag/test_structure_profile.py" -v
```
Expected: all PASS. Do not proceed to Step 2 until green.

- [ ] **Step 2: Re-run the KGE-structure line over 40 cases (spends API tokens)**

Requires `GRAPHRAG_API_KEY` (load it: `set -a; . ./.env; set +a`). Artifacts in
`kge_data/` already exist (do NOT retrain). Run:
```bash
cd KGE/KGE-based-graphrag && python nl_to_tio.py --prompt-profile structure_only \
  --test-cases ../../test_cases_40.json
```
Expected: 40 `.ttl` written to `tio_outputs/kge_structure/`; the printed context
per case is far shorter than the old ~8k-token dump (sanity-check one context has
the `@prefix` block and no `TransE score=` / `Predicted likely triples`).

- [ ] **Step 3: Evaluate and compare**

Run:
```bash
cd ../.. && python evaluate_ttl.py kge_structure --test-cases test_cases_40.json
```
Then compute composite + tok/case (reuse the aggregation already used for this
round) and compare against the recorded numbers: old KGE 0.0051 / 8,099,
GraphRAG-structure 0.7867 / 2,369, floor 0.0000 / 1,432. Confirm success per
spec §8: composite clearly off ~0, tok/case far below 8,099, output clean.

- [ ] **Step 4: Record results in `progress.md` and commit**

Add the canonical-KGE numbers to the "Experiment Architecture 3" table in
`progress.md` (replace the old KGE-structure row / add a "KGE-structure (canon)"
row), then:
```bash
git add progress.md phase1/phase1_kge_structure.json phase1/token_usage/token_usage_kge_structure.json tio_outputs/kge_structure
git commit -m "results(kge): canonical KGE-structure over 40 cases"
```

---

## Self-Review

**Spec coverage:**
- §3/§4 sound embedding use (text grounding + TransE real-triple ranking) → Task 1 (`transe_expand`) + Task 3 (`text_ground`). ✓
- §4 shared output contract → Task 2 (`assemble_context` reuses resource_index/graph_relations/context_builder). ✓
- §6 import GraphRag modules (sys.path) → Task 1/2 (`sys.path.insert(PROJECT_ROOT/"GraphRag")`). ✓
- §7.1 `select.py` functions → Tasks 1–3. ✓
- §7.2 remove misuses, keep loaders → Task 4. ✓
- §7.3 nl_to_tio swap → Task 5. ✓
- §8 evaluation + success → Task 6. ✓
- §9 testing (no synthetic triples; @prefix; reached-role vocab; no score/plumbing text; synonym grounding in online smoke) → Task 1/2 offline tests + Task 6 Step 2 smoke. ✓
- §10 train.py/artifacts untouched → no task modifies them. ✓

**Placeholder scan:** none — every code step shows complete code; Task 4's deletion lists exact function names; Task 6 is a run task with exact commands.

**Type consistency:** `transe_expand(seed_uris, *, top_k)`, `text_ground(query, *, top_k, case_id)`, `assemble_context(grounded_uris)`, `build_kge_context(query, *, case_id)` are referenced consistently across tasks; `select.py` imports only kept `retrieve.py` helpers (`_load_arrays`, `_load_kge_link_arrays`, `_load_triple_rows`, `_embed_query`, `trans_e_score`, `kge_ready`, `kge_link_prediction_ready`), which Task 4 preserves.

**Note:** `select.py` imports GraphRAG modules via `sys.path.insert(PROJECT_ROOT/"GraphRag")`; those modules (`ontology_graph`, `resource_index`, `graph_relations`, `context_builder`) already exist and are tested from the GraphRAG redesign.
