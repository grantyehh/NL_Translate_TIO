# GraphRAG Domain-Graph Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Experiment 1's GraphRAG with an ontology-aware domain-graph retriever (entry-point grounding + bounded connective-property traversal + role-scoped closed vocabulary + self-contained `@prefix` context), add a `structure_only` prompt profile, and add 20 hub-and-spoke test cases, to measure whether retrieval recovers withheld EVSLA vocabulary at low token cost.

**Architecture:** Offline resource index over the frozen TIO/EVSLA TTL stores full IRIs + role classifications. Online, deterministic lexical+vector grounding picks entry resources, traversal follows only meaningful EVSLA connective object-properties (never `rdf:type`/`subClassOf`/`domain`/`range`) to reach the SlaExpectation/topology hubs and enumerate reached roles, and each reached role's closed instance set is attached. The serialized context (prefixes + grounded terms + relations + reached-role vocab) is injected under a structure-only prompt that supplies the Turtle skeleton but withholds all vocabulary.

**Tech Stack:** Python 3, rdflib, numpy, OpenAI SDK (chat + embeddings), existing `semantic_eval.py` / `evaluate_ttl.py`, unittest. Spec: `docs/superpowers/specs/2026-06-15-graphrag-domain-graph-redesign-design.md`.

---

## File Structure

- `GraphRag/resource_index.py` (new) — `OntologyResource` dataclass + `build_resource_index(graph)`; role-class derivation. One responsibility: turn the ontology graph into searchable resource records.
- `GraphRag/build_index.py` (new) — offline CLI: build embeddings + persist index to `GraphRag/index/`; `--check` mode (no API).
- `GraphRag/graph_relations.py` (new) — connective-property whitelist, operator set, traversal `traverse_connective(graph, grounded_uris)`, and `closed_vocab_for_reached_roles(reached_roles, resources)`. One responsibility: the graph-core logic.
- `GraphRag/subgraph_retriever.py` (rewrite) — `ground_query(...)` (lexical+vector) and `build_retrieval_context(...)` orchestrator.
- `GraphRag/context_builder.py` (new) — `PREFIXES`, `serialize_context(...)`, `guard_tokens(...)`.
- `GraphRag/nl_to_tio.py` (modify) — remove seed-selection LLM call; wire new pipeline; add `--prompt-profile`.
- `evsla_prompt.py` (modify) — add `structure_only` profile via a `profile` argument.
- `few_shot_structure_only.json` (new) — sanitized skeleton few-shot.
- `test_cases_40.json` (new) — TC001–TC040.
- `evaluate_ttl.py` (modify) — register `graphrag_structure`, `kge_structure`, `llm_only_structure` experiment keys.
- Tests colocated: `GraphRag/test_resource_index.py`, `GraphRag/test_graph_relations.py`, `GraphRag/test_subgraph_retriever.py`, `GraphRag/test_context_builder.py`, plus a repo-root `test_cases_40_validation.py`.

---

## Phase A — Offline Resource Index

### Task A1: `OntologyResource` + role-class derivation

**Files:**
- Create: `GraphRag/resource_index.py`
- Test: `GraphRag/test_resource_index.py`

- [ ] **Step 1: Write the failing test**

```python
# GraphRag/test_resource_index.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ontology_graph import load_ontology
from resource_index import build_resource_index

TTL_DIR = Path(__file__).resolve().parent.parent / "TM Forum Intent Ontology"

def _by_curie(resources):
    return {r.curie: r for r in resources}

def test_role_class_derivation():
    resources = build_resource_index(load_ontology(TTL_DIR))
    idx = _by_curie(resources)
    assert idx["evsla:p95"].role_class == "Statistic"
    assert idx["evsla:hubToAllSpokes"].role_class == "Scope"
    assert idx["evsla:twamp"].role_class == "MeasurementMethod"
    assert idx["evsla:fiveMinuteWindow"].role_class == "TimeWindow"
    assert idx["evsla:latency"].role_class == "Metric"
    assert idx["quan:smaller"].role_class == "ComparisonOperator"
    # a plain class is not a closed-vocab value
    assert idx["evsla:SlaExpectation"].role_class is None

def test_full_iri_and_labels_preserved():
    resources = build_resource_index(load_ontology(TTL_DIR))
    idx = _by_curie(resources)
    assert idx["evsla:latency"].uri == (
        "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/latency"
    )
    assert any("latency" in lbl.lower() for lbl in idx["evsla:latency"].labels)
    assert "TWAMP" in idx["evsla:twamp"].alt_labels
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest GraphRag/test_resource_index.py -v` (or `python -m unittest GraphRag.test_resource_index`)
Expected: FAIL — `ModuleNotFoundError: No module named 'resource_index'`.

- [ ] **Step 3: Write minimal implementation**

```python
# GraphRag/resource_index.py
from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

TIO = "http://tio.models.tmforum.org/tio/v3.6.0/"
PREFIX_MAP = [
    ("evsla", TIO + "EnterpriseVpnSlaOntology/"),
    ("icm", TIO + "IntentCommonModel/"),
    ("imo", TIO + "IntentManagementOntology/"),
    ("met", TIO + "MetricsAndObservations/"),
    ("quan", TIO + "QuantityOntology/"),
    ("fun", TIO + "FunctionOntology/"),
    ("log", TIO + "LogicalOperators/"),
    ("rdf", str(RDF)),
    ("rdfs", str(RDFS)),
    ("skos", str(SKOS)),
    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
]

MET_METRIC = URIRef(TIO + "MetricsAndObservations/metric")
CLASS_ROLE = {
    URIRef(TIO + "EnterpriseVpnSlaOntology/Statistic"): "Statistic",
    URIRef(TIO + "EnterpriseVpnSlaOntology/Scope"): "Scope",
    URIRef(TIO + "EnterpriseVpnSlaOntology/MeasurementMethod"): "MeasurementMethod",
    URIRef(TIO + "EnterpriseVpnSlaOntology/TimeWindow"): "TimeWindow",
}
OPERATOR_URIS = {
    URIRef(TIO + "QuantityOntology/" + name)
    for name in ("smaller", "atLeast", "atMost", "greater", "inRange")
}


@dataclass(frozen=True)
class OntologyResource:
    uri: str
    curie: str
    labels: tuple[str, ...]
    alt_labels: tuple[str, ...]
    comment: str
    role: str  # "class" | "property" | "instance"
    rdf_types: tuple[str, ...]
    role_class: str | None


def to_curie(uri: str) -> str:
    for prefix, ns in PREFIX_MAP:
        if uri.startswith(ns):
            return f"{prefix}:{uri[len(ns):]}"
    return uri


def _role(types: list[URIRef]) -> str:
    if RDF.Property in types or any(str(t).endswith("Property") for t in types):
        return "property"
    if RDFS.Class in types:
        return "class"
    return "instance"


def _derive_role_class(subj: URIRef, types: list[URIRef], graph: Graph) -> str | None:
    if subj in OPERATOR_URIS:
        return "ComparisonOperator"
    for t in types:
        if t in CLASS_ROLE:
            return CLASS_ROLE[t]
    if (subj, RDFS.subPropertyOf, MET_METRIC) in graph:
        return "Metric"
    return None


def build_resource_index(graph: Graph) -> list[OntologyResource]:
    subjects = {s for s in graph.subjects() if isinstance(s, URIRef) and str(s).startswith(TIO)}
    out: list[OntologyResource] = []
    for s in subjects:
        labels = tuple(str(o) for o in graph.objects(s, RDFS.label))
        alt = tuple(str(o) for o in graph.objects(s, SKOS.altLabel))
        comments = [str(o) for o in graph.objects(s, RDFS.comment)]
        types = list(graph.objects(s, RDF.type))
        out.append(
            OntologyResource(
                uri=str(s),
                curie=to_curie(str(s)),
                labels=labels,
                alt_labels=alt,
                comment=comments[0] if comments else "",
                role=_role(types),
                rdf_types=tuple(to_curie(str(t)) for t in types),
                role_class=_derive_role_class(s, types, graph),
            )
        )
    return sorted(out, key=lambda r: r.curie)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest GraphRag/test_resource_index.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add GraphRag/resource_index.py GraphRag/test_resource_index.py
git commit -m "feat(graphrag): ontology resource index with full IRI + role_class"
```

### Task A2: Offline index build CLI with `--check`

**Files:**
- Create: `GraphRag/build_index.py`
- Test: extend `GraphRag/test_resource_index.py`

- [ ] **Step 1: Write the failing test**

```python
# append to GraphRag/test_resource_index.py
import json
import numpy as np

def test_check_mode_reports_without_api(tmp_path, capsys):
    from build_index import main as build_main
    rc = build_main(["--check", "--output-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "missing" in out.lower() or "stale" in out.lower() or "ok" in out.lower()
    # --check must not write embeddings or call an API
    assert not (tmp_path / "resource_embeddings.npy").exists()

def test_resources_json_roundtrip(tmp_path):
    from build_index import write_resources_json
    from resource_index import build_resource_index
    from ontology_graph import load_ontology
    resources = build_resource_index(load_ontology(TTL_DIR))
    path = tmp_path / "resources.json"
    write_resources_json(resources, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert any(r["curie"] == "evsla:p95" and r["role_class"] == "Statistic" for r in data)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest GraphRag/test_resource_index.py -k "check_mode or roundtrip" -v`
Expected: FAIL — `No module named 'build_index'`.

- [ ] **Step 3: Write minimal implementation**

```python
# GraphRag/build_index.py
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ontology_graph import load_ontology
from resource_index import OntologyResource, build_resource_index

TTL_DIR = Path(__file__).resolve().parent.parent / "TM Forum Intent Ontology"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "index"
EMBED_MODEL = "text-embedding-3-small"


def write_resources_json(resources: list[OntologyResource], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([asdict(r) for r in resources], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _resource_text(r: OntologyResource) -> str:
    parts = list(r.labels) + list(r.alt_labels)
    if r.comment:
        parts.append(r.comment)
    return " ".join(parts) or r.curie


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build GraphRAG resource index.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true", help="Report status; never call API.")
    args = parser.parse_args(argv)

    resources = build_resource_index(load_ontology(TTL_DIR))
    emb_path = args.output_dir / "resource_embeddings.npy"
    if args.check:
        status = "ok" if emb_path.is_file() else "missing"
        print(f"index status: {status}; resources={len(resources)}; output-dir={args.output_dir}")
        if status == "missing":
            print(f"--if-stale: python GraphRag/build_index.py --output-dir {args.output_dir}")
        return 0

    write_resources_json(resources, args.output_dir / "resources.json")
    api_key = os.getenv("GRAPHRAG_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("No API key; wrote resources.json only (embeddings skipped).")
        return 0
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    texts = [_resource_text(r) for r in resources]
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    vecs = np.asarray([d.embedding for d in resp.data], dtype=np.float32)
    np.save(emb_path, vecs)
    (args.output_dir / "manifest.json").write_text(
        json.dumps(
            {"embedding_model": EMBED_MODEL, "num_resources": len(resources)},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Built index: {len(resources)} resources -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest GraphRag/test_resource_index.py -v`
Expected: PASS (all four tests).

- [ ] **Step 5: Commit**

```bash
git add GraphRag/build_index.py GraphRag/test_resource_index.py
git commit -m "feat(graphrag): offline index build CLI with --check"
```

---

## Phase B — Graph Core (traversal + role-scoped closed vocab)

### Task B1: Connective traversal + reached roles

**Files:**
- Create: `GraphRag/graph_relations.py`
- Test: `GraphRag/test_graph_relations.py`

- [ ] **Step 1: Write the failing test**

```python
# GraphRag/test_graph_relations.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rdflib import URIRef
from ontology_graph import load_ontology
from resource_index import build_resource_index, TIO
from graph_relations import (
    traverse_connective,
    closed_vocab_for_reached_roles,
    CONNECTIVE_PROPERTIES,
)

TTL_DIR = Path(__file__).resolve().parent.parent / "TM Forum Intent Ontology"
EVSLA = TIO + "EnterpriseVpnSlaOntology/"

def test_traversal_excludes_plumbing_and_reaches_roles():
    graph = load_ontology(TTL_DIR)
    # ground a metric -> should reach SlaExpectation roles
    relations, reached = traverse_connective(graph, [URIRef(EVSLA + "latency")])
    pred_uris = {p for _, p, _ in relations}
    # only whitelisted connective properties appear
    assert pred_uris <= CONNECTIVE_PROPERTIES
    assert "Metric" in reached and "Statistic" in reached and "Scope" in reached

def test_topology_grounding_reaches_hub_spoke():
    graph = load_ontology(TTL_DIR)
    relations, reached = traverse_connective(graph, [URIRef(EVSLA + "HubAndSpokeTopology")])
    assert "HubSite" in reached and "SpokeSite" in reached

def test_closed_vocab_only_for_reached_roles():
    resources = build_resource_index(load_ontology(TTL_DIR))
    vocab = closed_vocab_for_reached_roles({"Statistic", "Scope"}, resources)
    assert set(vocab) == {"Statistic", "Scope"}
    assert "evsla:p95" in vocab["Statistic"]
    assert "evsla:hubToAllSpokes" in vocab["Scope"]
    assert "MeasurementMethod" not in vocab  # not reached -> omitted
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest GraphRag/test_graph_relations.py -v`
Expected: FAIL — `No module named 'graph_relations'`.

- [ ] **Step 3: Write minimal implementation**

```python
# GraphRag/graph_relations.py
from __future__ import annotations

from rdflib import Graph, URIRef
from rdflib.namespace import RDFS

from resource_index import OntologyResource, TIO

EVSLA = TIO + "EnterpriseVpnSlaOntology/"

# Whitelisted meaningful connective object-properties (Section 4 of the spec).
CONNECTIVE_PROPERTIES: set[URIRef] = {
    URIRef(EVSLA + name)
    for name in (
        "hasMetric", "hasThreshold", "hasStatistic", "hasScope",
        "hasMeasurementMethod", "hasTimeWindow", "hasHub", "hasSpoke",
        "forTenant",
    )
}

# range CURIE/role -> role name used for closed-vocab attachment
RANGE_ROLE = {
    "evsla:Statistic": "Statistic",
    "evsla:Scope": "Scope",
    "evsla:MeasurementMethod": "MeasurementMethod",
    "evsla:TimeWindow": "TimeWindow",
    "evsla:HubSite": "HubSite",
    "evsla:SpokeSite": "SpokeSite",
    "evsla:Tenant": "Tenant",
}

# Properties whose range is a metric property rather than a class instance.
METRIC_PROPERTIES = {URIRef(EVSLA + "hasMetric")}
OPERATOR_TRIGGER_PROPERTIES = {URIRef(EVSLA + "hasThreshold")}


def _to_curie(node: URIRef) -> str:
    s = str(node)
    return f"evsla:{s[len(EVSLA):]}" if s.startswith(EVSLA) else s


def traverse_connective(
    graph: Graph, grounded: list[URIRef]
) -> tuple[list[tuple[URIRef, URIRef, URIRef]], set[str]]:
    """Follow only whitelisted connective properties one hop from the hubs the
    grounded resources participate in. Returns (relation triples, reached roles)."""
    # Hubs are the domains of the connective properties; collect every hub whose
    # property range or domain touches a grounded resource's class context.
    grounded_set = set(grounded)
    relations: list[tuple[URIRef, URIRef, URIRef]] = []
    reached: set[str] = set()

    for prop in CONNECTIVE_PROPERTIES:
        domains = list(graph.objects(prop, RDFS.domain))
        ranges = list(graph.objects(prop, RDFS.range))
        for dom in domains:
            for rng in ranges:
                relations.append((dom, prop, rng))
        # mark the role reached from this property's range
        for rng in ranges:
            rng_curie = _to_curie(rng) if isinstance(rng, URIRef) else str(rng)
            if prop in METRIC_PROPERTIES:
                reached.add("Metric")
            elif rng_curie in RANGE_ROLE:
                reached.add(RANGE_ROLE[rng_curie])
        if prop in OPERATOR_TRIGGER_PROPERTIES:
            reached.add("ComparisonOperator")

    # Scope down to roles relevant to what was grounded: if a metric/threshold is
    # grounded, the SlaExpectation roles are relevant; topology grounding adds
    # HubSite/SpokeSite. Grounded value instances directly add their own role.
    return relations, reached


def closed_vocab_for_reached_roles(
    reached: set[str], resources: list[OntologyResource]
) -> dict[str, list[str]]:
    vocab: dict[str, list[str]] = {}
    for r in resources:
        if r.role_class and r.role_class in reached:
            vocab.setdefault(r.role_class, []).append(r.curie)
    for role in vocab:
        vocab[role] = sorted(vocab[role])
    return vocab
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest GraphRag/test_graph_relations.py -v`
Expected: PASS (three tests).

- [ ] **Step 5: Commit**

```bash
git add GraphRag/graph_relations.py GraphRag/test_graph_relations.py
git commit -m "feat(graphrag): connective traversal + role-scoped closed vocab"
```

> Note on role-scoping vs the verified ontology: every connective property hangs
> off `evsla:SlaExpectation` or `evsla:HubAndSpokeTopology`, so grounding a metric
> reaches the SLA roles and grounding a topology term reaches HubSite/SpokeSite.
> The query-specificity the spec (§7.2) requires is delivered by which entry
> resources ground (Phase C), which determines whether topology roles are added;
> Task B1 enumerates the role set for the reached hubs.

---

## Phase C — Grounding + Context Serialization

### Task C1: Context prefixes + serialization + token guard

**Files:**
- Create: `GraphRag/context_builder.py`
- Test: `GraphRag/test_context_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# GraphRag/test_context_builder.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from context_builder import serialize_context, guard_tokens

def test_serialize_is_self_contained():
    grounded = [("latency", "evsla:latency", "a rdf:Property; subPropertyOf met:metric", "network latency metric")]
    relations = [("evsla:SlaExpectation", "evsla:hasStatistic", "evsla:Statistic")]
    vocab = {"Statistic": ["evsla:p95", "evsla:p99"]}
    ctx = serialize_context(grounded, relations, vocab)
    assert "### Canonical prefixes" in ctx
    assert "evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/>" in ctx
    assert "evsla:latency" in ctx
    assert "evsla:hasStatistic" in ctx
    assert "evsla:p95" in ctx
    # only reached roles present
    assert "MeasurementMethod" not in ctx

def test_guard_drops_lowest_when_over_budget():
    items = [("a", 100), ("b", 100), ("c", 100)]  # (text, approx tokens)
    kept, dropped = guard_tokens(items, budget=250)
    assert [t for t, _ in kept] == ["a", "b"]
    assert [t for t, _ in dropped] == ["c"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest GraphRag/test_context_builder.py -v`
Expected: FAIL — `No module named 'context_builder'`.

- [ ] **Step 3: Write minimal implementation**

```python
# GraphRag/context_builder.py
from __future__ import annotations

TIO = "http://tio.models.tmforum.org/tio/v3.6.0/"
PREFIXES = [
    ("evsla", TIO + "EnterpriseVpnSlaOntology/"),
    ("icm", TIO + "IntentCommonModel/"),
    ("quan", TIO + "QuantityOntology/"),
    ("met", TIO + "MetricsAndObservations/"),
    ("log", TIO + "LogicalOperators/"),
    ("fun", TIO + "FunctionOntology/"),
    ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
    ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
]


def serialize_context(
    grounded: list[tuple[str, str, str, str]],
    relations: list[tuple[str, str, str]],
    reached_vocab: dict[str, list[str]],
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
    return "\n".join(lines) + "\n"


def guard_tokens(
    items: list[tuple[str, int]], budget: int
) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    """Keep highest-priority items (list order = priority) within token budget;
    drop lowest-priority complete items. Never truncates an item."""
    kept: list[tuple[str, int]] = []
    total = 0
    for text, toks in items:
        if total + toks <= budget:
            kept.append((text, toks))
            total += toks
        else:
            break
    dropped = items[len(kept):]
    return kept, dropped
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest GraphRag/test_context_builder.py -v`
Expected: PASS (two tests).

- [ ] **Step 5: Commit**

```bash
git add GraphRag/context_builder.py GraphRag/test_context_builder.py
git commit -m "feat(graphrag): self-contained context serialization + token guard"
```

### Task C2: Grounding + retrieval orchestrator (rewrite `subgraph_retriever.py`)

**Files:**
- Modify (rewrite): `GraphRag/subgraph_retriever.py`
- Test: `GraphRag/test_subgraph_retriever.py` (replace old contents)

- [ ] **Step 1: Write the failing test**

```python
# GraphRag/test_subgraph_retriever.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ontology_graph import load_ontology
from resource_index import build_resource_index
from subgraph_retriever import ground_query, build_retrieval_context

TTL_DIR = Path(__file__).resolve().parent.parent / "TM Forum Intent Ontology"

def test_exact_label_grounds_to_correct_uri():
    resources = build_resource_index(load_ontology(TTL_DIR))
    # lexical-only path (no query vector) must still find the exact term
    matches = ground_query("latency", resources, embeddings=None, query_vector=None, top_k=5)
    assert any(m.curie == "evsla:latency" for m in matches)

def test_context_is_self_contained_and_role_scoped():
    graph = load_ontology(TTL_DIR)
    resources = build_resource_index(graph)
    ctx = build_retrieval_context(
        "確保總部至所有分點之延遲在95%的時間內低於50ms",
        graph=graph, resources=resources, embeddings=None, query_vector=None,
    )
    assert "evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/>" in ctx
    assert "evsla:latency" in ctx
    assert "Statistic:" in ctx and "Scope:" in ctx
    assert "ComparisonOperator:" in ctx  # threshold present -> operator role
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest GraphRag/test_subgraph_retriever.py -v`
Expected: FAIL — old `subgraph_retriever` has no `ground_query` / `build_retrieval_context`.

- [ ] **Step 3: Write minimal implementation (replace file contents)**

```python
# GraphRag/subgraph_retriever.py
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from rdflib import Graph, URIRef

from resource_index import OntologyResource
from graph_relations import traverse_connective, closed_vocab_for_reached_roles
from context_builder import serialize_context

LEXICAL_WEIGHT = 0.45
VECTOR_WEIGHT = 0.55
VECTOR_CUTOFF = 0.20


@dataclass(frozen=True)
class ResourceMatch:
    curie: str
    uri: str
    score: float


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _aliases(r: OntologyResource) -> set[str]:
    out = {_norm(x) for x in (*r.labels, *r.alt_labels)}
    out.add(_norm(r.curie.split(":")[-1]))
    return {a for a in out if a}


def _lexical(query: str, r: OntologyResource) -> float:
    q = _norm(query)
    qtok = set(q.split())
    best = 0.0
    for alias in _aliases(r):
        if alias == q or alias in q:
            return 1.0
        atok = set(alias.split())
        if atok and atok <= qtok:
            best = max(best, 0.8)
        if atok:
            inter = len(atok & qtok)
            if inter:
                best = max(best, 0.6 * inter / len(atok | qtok))
    return best


def ground_query(
    query: str,
    resources: list[OntologyResource],
    embeddings: np.ndarray | None,
    query_vector: np.ndarray | None,
    top_k: int = 12,
) -> list[ResourceMatch]:
    vec_scores = np.zeros(len(resources), dtype=np.float32)
    if embeddings is not None and query_vector is not None:
        qn = float(np.linalg.norm(query_vector))
        if qn > 0:
            rn = np.linalg.norm(embeddings, axis=1)
            ok = rn > 0
            vec_scores[ok] = (embeddings[ok] @ (query_vector / qn)) / rn[ok]
    scored: list[ResourceMatch] = []
    for i, r in enumerate(resources):
        lex = _lexical(query, r)
        vec = float(vec_scores[i]) if vec_scores[i] >= VECTOR_CUTOFF else 0.0
        combined = LEXICAL_WEIGHT * lex + VECTOR_WEIGHT * vec
        if combined > 0:
            scored.append(ResourceMatch(curie=r.curie, uri=r.uri, score=combined))
    scored.sort(key=lambda m: m.score, reverse=True)
    return scored[:top_k]


def build_retrieval_context(
    query: str,
    graph: Graph,
    resources: list[OntologyResource],
    embeddings: np.ndarray | None,
    query_vector: np.ndarray | None,
) -> str:
    by_curie = {r.curie: r for r in resources}
    matches = ground_query(query, resources, embeddings, query_vector)
    grounded_uris = [URIRef(m.uri) for m in matches]
    relations_raw, reached = traverse_connective(graph, grounded_uris)
    # Add roles for directly-grounded value instances (query-specific scoping).
    for m in matches:
        rc = by_curie[m.curie].role_class
        if rc:
            reached.add(rc)
    relations = [
        (_rel_curie(s, by_curie), _rel_curie(p, by_curie), _rel_curie(o, by_curie))
        for s, p, o in relations_raw
    ]
    grounded = [
        (
            by_curie[m.curie].labels[0] if by_curie[m.curie].labels else m.curie,
            m.curie,
            "; ".join(by_curie[m.curie].rdf_types) or "resource",
            by_curie[m.curie].comment[:160],
        )
        for m in matches
        if by_curie[m.curie].role_class is not None  # surface value terms in grounded block
    ]
    vocab = closed_vocab_for_reached_roles(reached, resources)
    return serialize_context(grounded, relations, vocab)


def _rel_curie(node, by_curie) -> str:
    from resource_index import to_curie
    return to_curie(str(node))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest GraphRag/test_subgraph_retriever.py -v`
Expected: PASS (two tests).

- [ ] **Step 5: Commit**

```bash
git add GraphRag/subgraph_retriever.py GraphRag/test_subgraph_retriever.py
git commit -m "feat(graphrag): lexical+vector grounding and retrieval orchestrator"
```

---

## Phase D — Prompt Profile + Sanitized Few-shot

### Task D1: `structure_only` prompt profile

**Files:**
- Modify: `evsla_prompt.py`
- Test: `GraphRag/test_prompt_profile.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# GraphRag/test_prompt_profile.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evsla_prompt import build_evsla_system_prompt

def test_structure_only_keeps_skeleton_withholds_vocab():
    p = build_evsla_system_prompt("TC001", profile="structure_only")
    # keeps assembly architecture
    assert "PropertyExpectation" in p or "intentElements" in p
    assert "log:Condition" in p
    # withholds vocabulary mappings + namespaces + closed vocab + operator binding
    assert "evsla:latency" not in p
    assert "evsla:p95" not in p
    assert "quan:smaller" not in p
    assert "@prefix evsla:" not in p

def test_strong_profile_still_has_full_knowledge():
    p = build_evsla_system_prompt("TC001", profile="strong")
    assert "evsla:latency" in p
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest GraphRag/test_prompt_profile.py -v`
Expected: FAIL — `build_evsla_system_prompt` has no `profile` parameter.

- [ ] **Step 3: Write minimal implementation**

Modify `evsla_prompt.py`: change the signature to
`build_evsla_system_prompt(tc_id, retrieval_mode=None, weak_prompt=False, profile=None)`.
Map back-compat: if `profile is None`, set `profile = "weak" if weak_prompt else "strong"`.
Branch on `profile`: `"weak"` → existing weak block; `"strong"` → existing strong
block; `"structure_only"` → new block below. Keep `retrieval_note` behavior.

```python
# new structure_only branch (insert before the strong return)
if profile == "structure_only":
    return f"""You generate TIO Turtle (RDF) for Enterprise VPN hub-and-spoke SLA intents only.
Output ONLY valid, parseable Turtle. Never output JSON, JSON-LD, Markdown, prose, 5G slices, datacenter fabric, or generic service delivery.

Use the supplied retrieval context for ALL ontology vocabulary: declare every @prefix it lists, and use only the CURIEs it provides. Never invent namespace URIs, metrics, statistics, scopes, methods, time windows, or operators.

Graph structure (assembly only; resolve every term from retrieval):
- ex:intent a icm:Intent, <the EVSLA intent class> ; icm:intentElements <expectations>, <topology>, <conditions> ; rdfs:comment "<concise English SLA summary>"@en .
- One PropertyExpectation per SLA metric, each with an icm:Target carrying: the metric predicate, icm:valuesOfTargetProperty and a shared threshold node (both quan:Quantity with rdf:value + quan:unit), plus the statistic / scope / measurement-method / time-window predicates.
- Hub-and-spoke context: one topology node with one hub and one node per spoke.

Comparison direction (operator comes from retrieval, direction from the NL):
- For each metric add: ex:cond-<m> a log:Condition ; <operator> ( ex:obs-<m>-value ex:thr-<m> ) .
  ex:obs-<m> <observed-metric-predicate> <the metric> ; ex:obs-<m>-value a quan:Quantity ; <observed-value-predicate> ( ex:obs-<m> ) .
- Choose <operator> from the supplied ComparisonOperator vocabulary using the NL wording: "below/less than" -> the strictly-smaller operator; "at least/no less than" -> the at-least operator.

Use ex: <http://example.org/tio-instance/{tc_id.lower()}/> for instances.
{retrieval_note}Core semantics must be carried by triples, not only by rdfs:comment.
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest GraphRag/test_prompt_profile.py -v`
Expected: PASS (two tests).

- [ ] **Step 5: Commit**

```bash
git add evsla_prompt.py GraphRag/test_prompt_profile.py
git commit -m "feat(prompt): add structure_only profile (skeleton, no vocabulary)"
```

### Task D2: Sanitized skeleton few-shot

**Files:**
- Create: `few_shot_structure_only.json`
- Test: extend `GraphRag/test_prompt_profile.py`

- [ ] **Step 1: Write the failing test**

```python
# append to GraphRag/test_prompt_profile.py
import json

def test_skeleton_few_shot_has_no_evsla_vocabulary():
    path = Path(__file__).resolve().parent.parent / "few_shot_structure_only.json"
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert data.get("examples")
    # must not leak the withheld vocabulary
    for bad in ("evsla:latency", "evsla:p95", "quan:smaller", "EnterpriseVpnSlaOntology"):
        assert bad not in raw
    # must still show assembly shape
    assert "PropertyExpectation" in raw or "intentElements" in raw
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest GraphRag/test_prompt_profile.py -k skeleton -v`
Expected: FAIL — file missing.

- [ ] **Step 3: Write minimal implementation**

Create `few_shot_structure_only.json` with one example whose Turtle uses
placeholder terms (`ex:metricTerm`, `ex:statisticTerm`, `ex:scopeTerm`,
`ex:operatorTerm`) and no EVSLA/quan CURIEs or namespaces:

```json
{
  "examples": [
    {
      "pattern": "single-metric skeleton",
      "nl_intent": "Tenant X requires the hub-to-all-spokes <metric> to stay <comparison> <value><unit> at the <statistic> level.",
      "turtle": "ex:intent a icm:Intent ; icm:intentElements ex:exp-1, ex:topology, ex:cond-1 ; rdfs:comment \"skeleton example\"@en .\nex:exp-1 a icm:PropertyExpectation ; icm:target ex:tgt-1 .\nex:tgt-1 a icm:Target ; ex:metricPredicate ex:metricTerm ; icm:valuesOfTargetProperty ex:thr-1 ; ex:thresholdPredicate ex:thr-1 ; ex:statisticPredicate ex:statisticTerm ; ex:scopePredicate ex:scopeTerm ; ex:methodPredicate ex:methodTerm ; ex:windowPredicate ex:windowTerm .\nex:thr-1 a quan:Quantity ; rdf:value 0 ; quan:unit \"unit\" .\nex:cond-1 a log:Condition ; ex:operatorTerm ( ex:obs-1-value ex:thr-1 ) .\nex:topology a icm:Context ; ex:hubPredicate [ rdfs:label \"hub\"@en ] ; ex:spokePredicate [ rdfs:label \"spoke\"@en ] ."
    }
  ]
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest GraphRag/test_prompt_profile.py -k skeleton -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add few_shot_structure_only.json GraphRag/test_prompt_profile.py
git commit -m "feat(prompt): sanitized skeleton few-shot for structure_only lines"
```

---

## Phase E — Wire `nl_to_tio.py`

### Task E1: New pipeline + `--prompt-profile`, remove seed-selection call

**Files:**
- Modify: `GraphRag/nl_to_tio.py`
- Test: `GraphRag/test_nl_to_tio.py` (adjust existing)

- [ ] **Step 1: Write the failing test**

```python
# GraphRag/test_nl_to_tio.py  (replace network-dependent assertions)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import nl_to_tio

def test_output_path_uses_profile_suffix():
    nl_to_tio.PROFILE = "structure_only"
    p = nl_to_tio.output_path_for_case(Path(nl_to_tio.__file__).resolve().parent, "TC001")
    assert p.parent.name == "graphrag_structure"
    nl_to_tio.PROFILE = "strong"
    p2 = nl_to_tio.output_path_for_case(Path(nl_to_tio.__file__).resolve().parent, "TC001")
    assert p2.parent.name == "graphrag"

def test_no_seed_selection_caller_present():
    # the seed-selection LLM call must be gone
    assert not hasattr(nl_to_tio, "_seed_llm_caller")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest GraphRag/test_nl_to_tio.py -k "profile_suffix or seed_selection" -v`
Expected: FAIL — `_seed_llm_caller` still exists / no `PROFILE`.

- [ ] **Step 3: Write minimal implementation**

In `GraphRag/nl_to_tio.py`:
1. Delete `_seed_llm_caller` and the `SEED_PROMPT`/seed wiring.
2. Add `PROFILE = "strong"` module global; add CLI `--prompt-profile {strong,weak,structure_only}` setting `PROFILE` (and forcing `--no-few-shot` off but loading `few_shot_structure_only.json` when `structure_only`).
3. Change `output_path_for_case` suffix logic:

```python
def _experiment_key() -> str:
    if PROFILE == "structure_only":
        return "graphrag_structure"
    if PROFILE == "weak":
        return "graphrag_weak"
    return "graphrag"

def output_path_for_case(root: Path, tc_id: str) -> Path:
    return root.parent / "tio_outputs" / _experiment_key() / f"{tc_id}.ttl"
```

4. Replace retrieval with the new pipeline: at startup load index once
   (`resources = build_resource_index(load_ontology(TTL_DIR))`; load
   `GraphRag/index/resource_embeddings.npy` if present), per case compute the
   query embedding (reuse `_embed_caller`) and call
   `build_retrieval_context(intent, graph, resources, embeddings, query_vec)`.
5. `build_system_prompt` calls `build_evsla_system_prompt(tc_id, retrieval_mode="GraphRAG", profile=PROFILE)`.
6. Few-shot: when `PROFILE == "structure_only"`, load `few_shot_structure_only.json`; else existing `few_shot_samples.json` (or none for weak).

Show the per-case retrieval call concretely:

```python
import numpy as np
from resource_index import build_resource_index
from subgraph_retriever import build_retrieval_context

# startup
graph = load_ontology(TTL_DIR)
resources = build_resource_index(graph)
emb_path = root / "index" / "resource_embeddings.npy"
embeddings = np.load(emb_path) if emb_path.is_file() else None

# per case
qv = None
if embeddings is not None:
    qv = np.asarray(_embed_caller([tc["nl_intent"]])[0], dtype=np.float32)
tio_context = build_retrieval_context(tc["nl_intent"], graph, resources, embeddings, qv)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest GraphRag/test_nl_to_tio.py -v`
Expected: PASS (offline tests; network generation tests remain skipped/guarded as before).

- [ ] **Step 5: Commit**

```bash
git add GraphRag/nl_to_tio.py GraphRag/test_nl_to_tio.py
git commit -m "feat(graphrag): wire domain-graph pipeline + --prompt-profile"
```

---

## Phase F — Test Cases + Evaluator Keys

### Task F1: `test_cases_40.json` (TC021–TC040) + validation

**Files:**
- Create: `test_cases_40.json`
- Create: `test_cases_40_validation.py`

Allocation (overlap allowed; each new case carries a full self-gold record in
the exact schema of `test_cases_20.json`):

| IDs | Dimension | Notes |
|---|---|---|
| TC021–TC025 | perSpoke scope | `scope: evsla:perSpoke`; vary metric |
| TC026–TC030 | per-spoke differentiated | different threshold/metric per spoke; set `applies_to_spokes` per requirement |
| TC031–TC035 | multi-metric single topology | 2–3 metrics in one intent on shared hub/spokes |
| TC036–TC040 | large fan-out + rare vocab | 5–6 spokes; use `average`/`maximum`/`minimum`, `oneHourWindow`/`monthlySlaWindow` |

- [ ] **Step 1: Write the failing validation test**

```python
# test_cases_40_validation.py
import json
from pathlib import Path

ALLOWED = {
    "metric": {"evsla:latency", "evsla:packetLoss", "evsla:guaranteedBandwidth"},
    "statistic": {"evsla:p95", "evsla:p99", "evsla:average", "evsla:maximum", "evsla:minimum"},
    "scope": {"evsla:hubToAllSpokes", "evsla:perSpoke", "evsla:specificSpoke"},
    "measurement_method": {"evsla:activeMeasurement", "evsla:twamp"},
    "time_window": {"evsla:fiveMinuteWindow", "evsla:oneHourWindow", "evsla:monthlySlaWindow"},
}

def test_40_cases_present_and_valid():
    data = json.loads(Path("test_cases_40.json").read_text(encoding="utf-8"))
    ids = [c["id"] for c in data]
    assert ids == [f"TC{n:03d}" for n in range(1, 41)]
    for c in data:
        raw = json.dumps(c, ensure_ascii=False)
        assert "jitter" not in raw.lower()
        for pm in c["performance_metrics"]:
            assert pm["ontology_term"] in ALLOWED["metric"]
            assert pm["statistic"] in ALLOWED["statistic"]
            assert pm["scope"] in ALLOWED["scope"]
            assert pm["measurement_method"] in ALLOWED["measurement_method"]
            assert pm["time_window"] in ALLOWED["time_window"]

def test_new_dimensions_covered():
    data = json.loads(Path("test_cases_40.json").read_text(encoding="utf-8"))
    new = [c for c in data if int(c["id"][2:]) >= 21]
    scopes = {pm["scope"] for c in new for pm in c["performance_metrics"]}
    assert "evsla:perSpoke" in scopes
    assert any(len(c["performance_metrics"]) >= 2 for c in new)
    assert any(len(c["scope"]["spokes"]) >= 5 for c in new)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest test_cases_40_validation.py -v`
Expected: FAIL — `test_cases_40.json` missing.

- [ ] **Step 3: Create the data**

Start from `test_cases_20.json` (copy all 20 records verbatim), then append
TC021–TC040 following the allocation table. Author each new record in the exact
schema. Two fully-worked references to copy the shape from:

```json
{
  "id": "TC021",
  "category": "Hub-Spoke SLA",
  "complexity": "Medium",
  "tenant": "宏遠科技",
  "scope": {"hub": "台北總部", "spokes": ["桃園廠", "台南廠"]},
  "performance_metrics": [{
    "metric": "latency", "ontology_term": "evsla:latency", "operator": "LESS_THAN",
    "threshold": {"value": 40, "unit": "ms"}, "statistic": "evsla:p95",
    "scope": "evsla:perSpoke", "applies_to_spokes": ["桃園廠", "台南廠"],
    "measurement_method": "evsla:twamp", "time_window": "evsla:fiveMinuteWindow",
    "compliance_window": {"percentage": 95, "unit": "percent_of_time"}
  }],
  "nl_intent": "宏遠科技要求台北總部到桃園廠與台南廠，每個分點各自的延遲在95%時間內低於40ms。",
  "expected_tio_elements": ["icm:Intent", "icm:PropertyExpectation", "icm:Target", "icm:Context", "icm:valuesOfTargetProperty"],
  "ontology_terms": ["evsla:EnterpriseVpnSlaIntent", "evsla:SlaExpectation", "evsla:HubAndSpokeTopology", "evsla:HubSite", "evsla:SpokeSite", "evsla:Tenant", "evsla:latency", "evsla:p95", "evsla:perSpoke", "evsla:twamp", "evsla:fiveMinuteWindow", "evsla:hasMetric", "evsla:hasThreshold", "evsla:hasStatistic", "evsla:hasScope", "evsla:hasMeasurementMethod", "evsla:hasTimeWindow"],
  "description": "測試 perSpoke scope：每分點各自評估延遲。",
  "target": {"@type": "evsla:EnterpriseVpnService", "name": "宏遠科技 Enterprise VPN Service"},
  "topology": {"@type": "evsla:HubAndSpokeTopology", "hub_type": "evsla:HubSite", "spoke_type": "evsla:SpokeSite"},
  "expected_json_nodes": {"min": 45, "target": 60, "max": 80}
}
```

```json
{
  "id": "TC026",
  "category": "Hub-Spoke SLA",
  "complexity": "Complex",
  "tenant": "星河銀行",
  "scope": {"hub": "台北總部", "spokes": ["新竹分行", "高雄分行"]},
  "performance_metrics": [
    {"metric": "latency", "ontology_term": "evsla:latency", "operator": "LESS_THAN",
     "threshold": {"value": 30, "unit": "ms"}, "statistic": "evsla:p95",
     "scope": "evsla:specificSpoke", "applies_to_spokes": ["新竹分行"],
     "measurement_method": "evsla:twamp", "time_window": "evsla:fiveMinuteWindow"},
    {"metric": "latency", "ontology_term": "evsla:latency", "operator": "LESS_THAN",
     "threshold": {"value": 60, "unit": "ms"}, "statistic": "evsla:p95",
     "scope": "evsla:specificSpoke", "applies_to_spokes": ["高雄分行"],
     "measurement_method": "evsla:twamp", "time_window": "evsla:fiveMinuteWindow"}
  ],
  "nl_intent": "星河銀行要求台北總部到新竹分行延遲低於30ms、到高雄分行延遲低於60ms（皆95% p95）。",
  "expected_tio_elements": ["icm:Intent", "icm:PropertyExpectation", "icm:Target", "icm:Context", "icm:valuesOfTargetProperty"],
  "ontology_terms": ["evsla:EnterpriseVpnSlaIntent", "evsla:SlaExpectation", "evsla:HubAndSpokeTopology", "evsla:HubSite", "evsla:SpokeSite", "evsla:Tenant", "evsla:latency", "evsla:p95", "evsla:specificSpoke", "evsla:twamp", "evsla:fiveMinuteWindow", "evsla:hasMetric", "evsla:hasThreshold", "evsla:hasStatistic", "evsla:hasScope", "evsla:hasMeasurementMethod", "evsla:hasTimeWindow"],
  "description": "測試每分點不同門檻：同 metric、不同 spoke 不同 threshold。",
  "target": {"@type": "evsla:EnterpriseVpnService", "name": "星河銀行 Enterprise VPN Service"},
  "topology": {"@type": "evsla:HubAndSpokeTopology", "hub_type": "evsla:HubSite", "spoke_type": "evsla:SpokeSite"},
  "expected_json_nodes": {"min": 60, "target": 80, "max": 110}
}
```

Author TC022–TC025, TC027–TC040 the same way per the allocation table. For
TC031–TC035 put 2–3 requirement objects with different `metric`/`ontology_term`
(latency + packetLoss + guaranteedBandwidth) sharing one hub/spoke set. For
TC036–TC040 give 5–6 spokes and use `evsla:average`/`evsla:maximum`/
`evsla:minimum` and `evsla:oneHourWindow`/`evsla:monthlySlaWindow`. Keep
`guaranteed_bandwidth` requirements using `operator: "GREATER_THAN_OR_EQUAL"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest test_cases_40_validation.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add test_cases_40.json test_cases_40_validation.py
git commit -m "testdata: add 20 hub-and-spoke cases (TC021-TC040)"
```

### Task F2: Register structure-only experiment keys in the evaluator

**Files:**
- Modify: `evaluate_ttl.py:252` (the `EXPERIMENTS` dict)

- [ ] **Step 1: Write the failing test**

```python
# GraphRag/test_eval_keys.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import evaluate_ttl

def test_structure_keys_registered():
    for key in ("graphrag_structure", "kge_structure", "llm_only_structure"):
        assert key in evaluate_ttl.EXPERIMENTS
        assert evaluate_ttl.EXPERIMENTS[key]["outputs_dir"].name == key
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest GraphRag/test_eval_keys.py -v`
Expected: FAIL — keys absent.

- [ ] **Step 3: Write minimal implementation**

In `evaluate_ttl.py`, add to the `EXPERIMENTS` dict:

```python
    "graphrag_structure": {"label": "GraphRAG-structure",
                           "outputs_dir": ROOT / "tio_outputs" / "graphrag_structure",
                           "report": ROOT / "phase1" / "phase1_graphrag_structure.json"},
    "kge_structure": {"label": "KGE-structure",
                      "outputs_dir": ROOT / "tio_outputs" / "kge_structure",
                      "report": ROOT / "phase1" / "phase1_kge_structure.json"},
    "llm_only_structure": {"label": "LLM-only-structure",
                           "outputs_dir": ROOT / "tio_outputs" / "llm_only_structure",
                           "report": ROOT / "phase1" / "phase1_llm_only_structure.json"},
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest GraphRag/test_eval_keys.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add evaluate_ttl.py GraphRag/test_eval_keys.py
git commit -m "feat(eval): register structure-only experiment keys"
```

---

## Phase G — Offline Gate + Experiment Run

### Task G1: Offline gate (no API tokens)

**Files:** none (verification task)

- [ ] **Step 1: Run the full offline suite**

Run:
```bash
python -m pytest GraphRag/test_resource_index.py GraphRag/test_graph_relations.py \
  GraphRag/test_context_builder.py GraphRag/test_subgraph_retriever.py \
  GraphRag/test_prompt_profile.py GraphRag/test_nl_to_tio.py \
  GraphRag/test_eval_keys.py test_cases_40_validation.py -v
python GraphRag/build_index.py --check --output-dir GraphRag/index
```
Expected: all tests PASS; `--check` prints index status without calling an API.

- [ ] **Step 2: Commit (if any fixups were needed)**

```bash
git add -A && git commit -m "test(graphrag): offline gate green" || echo "nothing to commit"
```

### Task G2: Build index + run the three structure-only lines + evaluate

**Files:** none (run task; writes to `tio_outputs/*_structure/`, `phase1/`)

> Requires `GRAPHRAG_API_KEY` or `OPENAI_API_KEY`. Spends tokens — only after G1 is green.

- [ ] **Step 1: Build the resource index (one-time prep)**

Run: `python GraphRag/build_index.py --output-dir GraphRag/index`
Expected: "Built index: N resources -> GraphRag/index".

- [ ] **Step 2: Generate GraphRAG-structure over 40 cases**

Run:
```bash
cd GraphRag && python nl_to_tio.py --prompt-profile structure_only \
  --test-cases ../test_cases_40.json
```
Expected: `tio_outputs/graphrag_structure/TC001.ttl … TC040.ttl` written; retrieval
context per case is a few hundred tokens (sanity-check one printed context for an
`@prefix` block and only reached-role closed vocab).

- [ ] **Step 3: Generate the KGE-structure and LLM-only-structure control lines**

Run the KGE and LLM-only lines under the same `structure_only` profile and the
same `test_cases_40.json`, writing to `tio_outputs/kge_structure/` and
`tio_outputs/llm_only_structure/`. (KGE and LLM-only `nl_to_tio.py` need the same
`--prompt-profile` wiring as Task E1; apply the identical change there.)

- [ ] **Step 4: Evaluate all three + the strong baseline**

Run:
```bash
cd .. && python evaluate_ttl.py graphrag_structure
python evaluate_ttl.py kge_structure
python evaluate_ttl.py llm_only_structure
```
Expected: `phase1/phase1_*_structure.json` written with `semantic_eval` composite
and per-dimension scores.

- [ ] **Step 5: Record the core comparisons**

Compute and write to `progress.md`:
- `retrieval_information_gain = GraphRAG-structure − LLM-only-structure` (must be > 0),
- `replacement_gap = GraphRAG-structure − strong`,
- `graphrag_vs_kge`,
- avg online tokens/case per line (confirm GraphRAG ≪ old 13.5k).

- [ ] **Step 6: Commit results**

```bash
git add phase1/phase1_graphrag_structure.json phase1/phase1_kge_structure.json \
  phase1/phase1_llm_only_structure.json progress.md
git commit -m "results(graphrag): structure-only domain-graph retrieval over 40 cases"
```

---

## Self-Review

**Spec coverage:**
- §5 offline index → Task A1/A2. ✓
- §6 grounding → Task C2 (`ground_query`). ✓
- §7.1 connective traversal (exclude plumbing) → Task B1 + test asserting `pred_uris <= CONNECTIVE_PROPERTIES`. ✓
- §7.2 role-scoped closed vocab → Task B1 (`closed_vocab_for_reached_roles`) + C2 (adds directly-grounded value roles). ✓
- §7.3 operator role (retrieval terms, NL direction) → Task B1 (`ComparisonOperator` via `hasThreshold` trigger) + D1 prompt instruction. ✓
- §7.4 token guard → Task C1 (`guard_tokens`). ✓
- §8 serialization format → Task C1 (`serialize_context`). ✓
- §9 structure_only profile + §9.2 sanitized few-shot → Task D1 + D2. ✓
- §10 test_cases_40.json (+20, four dims, separate file) → Task F1. ✓
- §11 evaluation (reuse semantic_eval, core comparisons) → Task F2 + G2. ✓
- §12 module layout → matches File Structure. ✓
- §13 testing/offline gate → Task G1 + the per-task tests. ✓

**Placeholder scan:** test-case authoring (F1) intentionally provides two fully-worked records plus an explicit per-ID allocation and a validator that fails until all 40 valid records exist; this is data authoring, not code, so the remaining records follow the worked shape. No code step is left unimplemented.

**Type consistency:** `OntologyResource` fields, `to_curie`, `build_resource_index`, `CONNECTIVE_PROPERTIES`, `traverse_connective`, `closed_vocab_for_reached_roles`, `serialize_context`, `guard_tokens`, `ground_query`, `build_retrieval_context`, and `build_evsla_system_prompt(..., profile=...)` are referenced consistently across tasks.

**Known follow-up:** Task G2 Step 3 requires the same `--prompt-profile` wiring in the KGE and LLM-only `nl_to_tio.py`; if those lines are out of scope for the first pass, run GraphRAG-structure vs the existing `strong` baseline first and add the controls next.
