# GraphRAG Typed Traversal Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `GraphRag/` pipeline 從「呼叫 Microsoft `graphrag` CLI 取 chunk」改造成「rdflib 載入 TTL → label/type/comment 三種 index → 2-hop typed BFS → 子圖序列化」，讓 LLM 看到結構化 triple list 而非散文 chunk。

**Architecture:** 三層分離 — `ontology_graph.py`（純 RDF 載入與索引，無 LLM 依賴）、`subgraph_retriever.py`（seed 抽取 + URI grounding + 子圖展開 + 序列化，有 LLM/embedding 依賴）、`nl_to_tio.py`（既有 orchestrator，替換 `query_graphrag_local` 一個呼叫點）。LLM 與 embedding 呼叫透過 dependency injection 注入，方便測試 mock。

**Tech Stack:** Python 3.11+, `rdflib`, `openai` SDK (chat completions + text embeddings)、`numpy`、`unittest` + `unittest.mock`。

**Spec reference:** `docs/comparison_plan.md` §4。

---

## File Structure

| 路徑 | 角色 | 行數估計 |
|---|---|---|
| `GraphRag/ontology_graph.py` | 新檔：載入 TTL、建 label/type/comment index | ~120 |
| `GraphRag/subgraph_retriever.py` | 新檔：seed → URI → 2-hop subgraph → 序列化 | ~150 |
| `GraphRag/test_ontology_graph.py` | 新檔：unit tests，純 rdflib，無外部 IO | ~120 |
| `GraphRag/test_subgraph_retriever.py` | 新檔：unit tests，LLM/embedding 用 mock | ~150 |
| `GraphRag/nl_to_tio.py` | 修改：替換 `query_graphrag_local` 呼叫點 | -50 / +30 |
| `GraphRag/test_nl_to_tio.py` | 修改：移除 `test_graphrag_query_focuses_on_evsla_terms`（舊 API 已換） | -10 / +20 |

不動：`evsla_prompt.py`、`few_shot_samples.json`、`test_cases_20.json`、`evaluate_jsonld.py`、`compare_reports.py`、`jsonld_outputs/llm_only/`。

---

## Task 1: 載入所有 TTL 為單一 rdflib Graph

**Files:**
- Create: `GraphRag/ontology_graph.py`
- Create: `GraphRag/test_ontology_graph.py`

- [ ] **Step 1: Write the failing test**

```python
# GraphRag/test_ontology_graph.py
import unittest
from pathlib import Path

from ontology_graph import load_ontology


REPO_ROOT = Path(__file__).resolve().parent.parent
TTL_DIR = REPO_ROOT / "TM Forum Intent Ontology"


class TestLoadOntology(unittest.TestCase):
    def test_load_ontology_returns_non_empty_graph(self):
        g = load_ontology(TTL_DIR)
        self.assertGreater(len(g), 0)

    def test_load_ontology_includes_evsla_terms(self):
        g = load_ontology(TTL_DIR)
        from rdflib import URIRef
        evsla_twamp = URIRef("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/twamp")
        self.assertTrue(
            any(s == evsla_twamp for s, _, _ in g),
            "evsla:twamp should be a subject in the merged graph",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_ontology_graph -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ontology_graph'`

- [ ] **Step 3: Implement minimal `load_ontology`**

```python
# GraphRag/ontology_graph.py
from __future__ import annotations

from pathlib import Path

from rdflib import Graph


def load_ontology(ttl_dir: Path) -> Graph:
    """Load and merge all .ttl files in ttl_dir into a single rdflib Graph."""
    g = Graph()
    for ttl_path in sorted(Path(ttl_dir).glob("*.ttl")):
        g.parse(ttl_path, format="turtle")
    return g
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_ontology_graph -v`
Expected: PASS, both tests green.

- [ ] **Step 5: Commit**

```bash
git add GraphRag/ontology_graph.py GraphRag/test_ontology_graph.py
git commit -m "feat(graphrag): load all TIO TTL files into single rdflib Graph"
```

---

## Task 2: Label index (rdfs:label + skos:altLabel → URI)

**Files:**
- Modify: `GraphRag/ontology_graph.py`
- Modify: `GraphRag/test_ontology_graph.py`

- [ ] **Step 1: Write the failing test**

Append to `GraphRag/test_ontology_graph.py`:

```python
class TestLabelIndex(unittest.TestCase):
    def setUp(self):
        from ontology_graph import load_ontology, build_label_index
        self.idx = build_label_index(load_ontology(TTL_DIR))

    def test_label_index_maps_twamp_to_evsla_uri(self):
        self.assertIn("twamp", self.idx)
        self.assertEqual(
            str(self.idx["twamp"]),
            "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/twamp",
        )

    def test_label_index_includes_alt_label(self):
        # evsla:twamp has skos:altLabel "TWAMP"
        self.assertIn("twamp", self.idx)  # case-insensitive normalised

    def test_label_index_handles_multi_word_labels(self):
        self.assertIn("p95 statistic", self.idx)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_ontology_graph -v`
Expected: FAIL — `cannot import name 'build_label_index'`.

- [ ] **Step 3: Implement `build_label_index`**

Add to `GraphRag/ontology_graph.py`:

```python
from rdflib import Graph, URIRef
from rdflib.namespace import RDFS, SKOS


def build_label_index(graph: Graph) -> dict[str, URIRef]:
    """Map normalised label string (lowercase, stripped) → URI.

    Sources: rdfs:label and skos:altLabel. If multiple URIs share a label,
    the lexicographically smallest URI wins (deterministic).
    """
    index: dict[str, URIRef] = {}
    for predicate in (RDFS.label, SKOS.altLabel):
        for subject, _, literal in graph.triples((None, predicate, None)):
            if not isinstance(subject, URIRef):
                continue
            key = str(literal).strip().lower()
            if not key:
                continue
            if key not in index or str(subject) < str(index[key]):
                index[key] = subject
    return index
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_ontology_graph -v`
Expected: PASS, three new tests green.

- [ ] **Step 5: Commit**

```bash
git add GraphRag/ontology_graph.py GraphRag/test_ontology_graph.py
git commit -m "feat(graphrag): add label index over rdfs:label and skos:altLabel"
```

---

## Task 3: Type index (rdf:type → set of instance URIs)

**Files:**
- Modify: `GraphRag/ontology_graph.py`
- Modify: `GraphRag/test_ontology_graph.py`

- [ ] **Step 1: Write the failing test**

Append to `GraphRag/test_ontology_graph.py`:

```python
class TestTypeIndex(unittest.TestCase):
    def setUp(self):
        from ontology_graph import load_ontology, build_type_index
        self.idx = build_type_index(load_ontology(TTL_DIR))

    def test_type_index_lists_scope_instances(self):
        from rdflib import URIRef
        scope_cls = URIRef("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/Scope")
        instances = {str(u) for u in self.idx[scope_cls]}
        self.assertIn(
            "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/hubToAllSpokes",
            instances,
        )
        self.assertIn(
            "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/perSpoke",
            instances,
        )
        self.assertIn(
            "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/specificSpoke",
            instances,
        )

    def test_type_index_lists_statistic_instances(self):
        from rdflib import URIRef
        stat_cls = URIRef("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/Statistic")
        instances = {str(u) for u in self.idx[stat_cls]}
        self.assertIn(
            "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/p95",
            instances,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_ontology_graph -v`
Expected: FAIL — `cannot import name 'build_type_index'`.

- [ ] **Step 3: Implement `build_type_index`**

Add to `GraphRag/ontology_graph.py`:

```python
from collections import defaultdict
from rdflib.namespace import RDF


def build_type_index(graph: Graph) -> dict[URIRef, set[URIRef]]:
    """Map class URI → set of URIs that are rdf:type of that class."""
    index: dict[URIRef, set[URIRef]] = defaultdict(set)
    for subject, _, cls in graph.triples((None, RDF.type, None)):
        if isinstance(subject, URIRef) and isinstance(cls, URIRef):
            index[cls].add(subject)
    return dict(index)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_ontology_graph -v`
Expected: PASS, two new tests green.

- [ ] **Step 5: Commit**

```bash
git add GraphRag/ontology_graph.py GraphRag/test_ontology_graph.py
git commit -m "feat(graphrag): add type index mapping class URI to instance URIs"
```

---

## Task 4: Comment index (URI → rdfs:comment text)

**Files:**
- Modify: `GraphRag/ontology_graph.py`
- Modify: `GraphRag/test_ontology_graph.py`

This task does **not** call any embedding API — it only collects raw comment strings. Embedding is layered on top in Task 6.

- [ ] **Step 1: Write the failing test**

Append to `GraphRag/test_ontology_graph.py`:

```python
class TestCommentIndex(unittest.TestCase):
    def setUp(self):
        from ontology_graph import load_ontology, build_comment_index
        self.idx = build_comment_index(load_ontology(TTL_DIR))

    def test_comment_index_has_evsla_latency(self):
        from rdflib import URIRef
        uri = URIRef("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/latency")
        self.assertIn(uri, self.idx)
        self.assertIn("latency", self.idx[uri].lower())

    def test_comment_index_has_evsla_hubtoallspokes(self):
        from rdflib import URIRef
        uri = URIRef("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/hubToAllSpokes")
        self.assertIn(uri, self.idx)
        self.assertIn("spoke", self.idx[uri].lower())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_ontology_graph -v`
Expected: FAIL — `cannot import name 'build_comment_index'`.

- [ ] **Step 3: Implement `build_comment_index`**

Add to `GraphRag/ontology_graph.py`:

```python
def build_comment_index(graph: Graph) -> dict[URIRef, str]:
    """Map URI → its first rdfs:comment string. Skips URIs with no comment."""
    index: dict[URIRef, str] = {}
    for subject, _, literal in graph.triples((None, RDFS.comment, None)):
        if isinstance(subject, URIRef) and subject not in index:
            index[subject] = str(literal)
    return index
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_ontology_graph -v`
Expected: PASS, two new tests green.

- [ ] **Step 5: Commit**

```bash
git add GraphRag/ontology_graph.py GraphRag/test_ontology_graph.py
git commit -m "feat(graphrag): add comment index mapping URI to rdfs:comment"
```

---

## Task 5: 2-hop typed BFS over whitelisted predicates

**Files:**
- Modify: `GraphRag/ontology_graph.py`
- Modify: `GraphRag/test_ontology_graph.py`

The BFS follows only these edges (both directions): `rdfs:subClassOf`, `rdfs:subPropertyOf`, `rdf:type`, `rdfs:domain`, `rdfs:range`. Other edges (e.g. `dct:created`, `skos:changeNote`) are ignored to keep the subgraph focused.

- [ ] **Step 1: Write the failing test**

Append to `GraphRag/test_ontology_graph.py`:

```python
class TestTypedBfs(unittest.TestCase):
    def setUp(self):
        from ontology_graph import load_ontology, typed_bfs_subgraph
        self.graph = load_ontology(TTL_DIR)
        self.typed_bfs_subgraph = typed_bfs_subgraph

    def test_bfs_from_sla_expectation_includes_property_expectation(self):
        from rdflib import URIRef
        seed = URIRef("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/SlaExpectation")
        triples = self.typed_bfs_subgraph(self.graph, [seed], hops=2)
        objects = {str(o) for _, _, o in triples}
        # evsla:SlaExpectation rdfs:subClassOf icm:PropertyExpectation
        self.assertIn(
            "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/PropertyExpectation",
            objects,
        )

    def test_bfs_from_latency_finds_metric_super_property(self):
        from rdflib import URIRef
        seed = URIRef("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/latency")
        triples = self.typed_bfs_subgraph(self.graph, [seed], hops=2)
        objects = {str(o) for _, _, o in triples}
        self.assertIn(
            "http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/metric",
            objects,
        )

    def test_bfs_stops_at_hop_limit(self):
        from rdflib import URIRef
        seed = URIRef("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/twamp")
        zero_hop = self.typed_bfs_subgraph(self.graph, [seed], hops=0)
        self.assertEqual(zero_hop, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_ontology_graph -v`
Expected: FAIL — `cannot import name 'typed_bfs_subgraph'`.

- [ ] **Step 3: Implement `typed_bfs_subgraph`**

Add to `GraphRag/ontology_graph.py`:

```python
from rdflib.term import Node

TRAVERSAL_PREDICATES = (
    RDFS.subClassOf,
    RDFS.subPropertyOf,
    RDF.type,
    RDFS.domain,
    RDFS.range,
)


def typed_bfs_subgraph(
    graph: Graph,
    seeds: list[URIRef],
    hops: int,
) -> list[tuple[Node, Node, Node]]:
    """Return triples reachable from any seed within `hops` BFS steps,
    following only TRAVERSAL_PREDICATES in either direction."""
    if hops <= 0:
        return []
    visited: set[URIRef] = set()
    frontier: set[URIRef] = {s for s in seeds if isinstance(s, URIRef)}
    collected: set[tuple[Node, Node, Node]] = set()

    for _ in range(hops):
        next_frontier: set[URIRef] = set()
        for node in frontier:
            if node in visited:
                continue
            visited.add(node)
            for predicate in TRAVERSAL_PREDICATES:
                for _, _, obj in graph.triples((node, predicate, None)):
                    collected.add((node, predicate, obj))
                    if isinstance(obj, URIRef) and obj not in visited:
                        next_frontier.add(obj)
                for subj, _, _ in graph.triples((None, predicate, node)):
                    collected.add((subj, predicate, node))
                    if isinstance(subj, URIRef) and subj not in visited:
                        next_frontier.add(subj)
        frontier = next_frontier
        if not frontier:
            break

    return sorted(collected, key=lambda t: (str(t[0]), str(t[1]), str(t[2])))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_ontology_graph -v`
Expected: PASS, three new tests green.

- [ ] **Step 5: Commit**

```bash
git add GraphRag/ontology_graph.py GraphRag/test_ontology_graph.py
git commit -m "feat(graphrag): add 2-hop typed BFS over rdfs/rdf structural predicates"
```

---

## Task 6: Seed extractor (NL → list of seed strings) via LLM

**Files:**
- Create: `GraphRag/subgraph_retriever.py`
- Create: `GraphRag/test_subgraph_retriever.py`

The LLM call is injected as a `seed_caller: Callable[[str], str]` so tests can supply a fake instead of hitting OpenAI.

- [ ] **Step 1: Write the failing test**

```python
# GraphRag/test_subgraph_retriever.py
import json
import unittest

from subgraph_retriever import extract_seeds


class TestExtractSeeds(unittest.TestCase):
    def test_extract_seeds_parses_json_array_from_llm(self):
        def fake_caller(prompt: str) -> str:
            return json.dumps(["latency", "p95", "TWAMP", "hub to all spokes"])

        seeds = extract_seeds("確保總部至所有分點延遲95%時間內低於50ms", caller=fake_caller)

        self.assertEqual(seeds, ["latency", "p95", "TWAMP", "hub to all spokes"])

    def test_extract_seeds_strips_code_fences(self):
        def fake_caller(prompt: str) -> str:
            return '```json\n["latency", "p95"]\n```'

        seeds = extract_seeds("dummy", caller=fake_caller)

        self.assertEqual(seeds, ["latency", "p95"])

    def test_extract_seeds_returns_empty_on_invalid_json(self):
        def fake_caller(prompt: str) -> str:
            return "not json"

        seeds = extract_seeds("dummy", caller=fake_caller)

        self.assertEqual(seeds, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_subgraph_retriever -v`
Expected: FAIL — `No module named 'subgraph_retriever'`.

- [ ] **Step 3: Implement `extract_seeds`**

Create `GraphRag/subgraph_retriever.py`:

```python
from __future__ import annotations

import json
import re
from typing import Callable

SEED_PROMPT = """You extract ontology-relevant terms from a network intent.
Output a JSON array of short English terms (1-3 words each), no commentary.
Cover: metric (e.g. latency, packet loss), statistic (p95, p99, average),
scope (hub to all spokes, per spoke, specific spoke), measurement method (TWAMP),
time window (5 minute, hourly, monthly).
Skip tenant names, site names, numbers, and units."""


def _strip_code_fence(text: str) -> str:
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```\s*$", text.strip(), re.DOTALL)
    if fence:
        return fence.group(1)
    return text


def extract_seeds(nl_intent: str, caller: Callable[[str], str]) -> list[str]:
    """Call LLM (via injected caller) to extract a list of ontology seed terms."""
    user_msg = f"{SEED_PROMPT}\n\nIntent: {nl_intent}"
    raw = caller(user_msg)
    raw = _strip_code_fence(raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if isinstance(item, (str, int, float))]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_subgraph_retriever -v`
Expected: PASS, three tests green.

- [ ] **Step 5: Commit**

```bash
git add GraphRag/subgraph_retriever.py GraphRag/test_subgraph_retriever.py
git commit -m "feat(graphrag): add LLM-backed seed term extractor with injectable caller"
```

---

## Task 7: Seed-to-URI grounding via label index + comment embedding fallback

**Files:**
- Modify: `GraphRag/subgraph_retriever.py`
- Modify: `GraphRag/test_subgraph_retriever.py`

Embedding caller signature: `embed_caller: Callable[[list[str]], list[list[float]]]`. Batched call returns one vector per string in the same order.

- [ ] **Step 1: Write the failing test**

Append to `GraphRag/test_subgraph_retriever.py`:

```python
from rdflib import URIRef


class TestGroundSeeds(unittest.TestCase):
    def test_ground_seeds_uses_label_index_when_available(self):
        from subgraph_retriever import ground_seeds

        label_idx = {
            "twamp": URIRef("http://example.org/evsla/twamp"),
            "p95 statistic": URIRef("http://example.org/evsla/p95"),
        }

        grounded = ground_seeds(
            ["TWAMP", "p95 statistic"],
            label_index=label_idx,
            comment_index={},
            embed_caller=lambda items: [],
        )

        self.assertIn(URIRef("http://example.org/evsla/twamp"), grounded)
        self.assertIn(URIRef("http://example.org/evsla/p95"), grounded)

    def test_ground_seeds_falls_back_to_comment_similarity(self):
        from subgraph_retriever import ground_seeds

        uri = URIRef("http://example.org/evsla/hubToAllSpokes")
        comment_idx = {uri: "The SLA metric is evaluated from the hub site to all spoke sites."}

        # Embed: returns identical vector for seed and comment → cosine = 1
        def fake_embed(items):
            return [[1.0, 0.0] for _ in items]

        grounded = ground_seeds(
            ["hub to all spokes"],
            label_index={},
            comment_index=comment_idx,
            embed_caller=fake_embed,
            similarity_threshold=0.5,
        )

        self.assertIn(uri, grounded)

    def test_ground_seeds_skips_when_no_match(self):
        from subgraph_retriever import ground_seeds

        def fake_embed(items):
            # First item (seed) is [1, 0]; comment items are orthogonal [0, 1]
            return [[1.0, 0.0]] + [[0.0, 1.0] for _ in items[1:]]

        grounded = ground_seeds(
            ["nonexistent term"],
            label_index={},
            comment_index={URIRef("http://example.org/x"): "completely unrelated"},
            embed_caller=fake_embed,
            similarity_threshold=0.9,
        )

        self.assertEqual(grounded, set())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_subgraph_retriever -v`
Expected: FAIL — `cannot import name 'ground_seeds'`.

- [ ] **Step 3: Implement `ground_seeds`**

Add to `GraphRag/subgraph_retriever.py`:

```python
import math
from rdflib import URIRef


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def ground_seeds(
    seeds: list[str],
    label_index: dict[str, URIRef],
    comment_index: dict[URIRef, str],
    embed_caller: Callable[[list[str]], list[list[float]]],
    similarity_threshold: float = 0.6,
) -> set[URIRef]:
    """Resolve each seed string to a URI using label index first, then comment-embedding cosine.

    Seeds with no label hit fall through to the embedding fallback.
    If multiple seeds need fallback, embeddings are computed in one batched call
    (seeds first, then all comment values) for efficiency.
    """
    resolved: set[URIRef] = set()
    unresolved: list[str] = []

    for seed in seeds:
        key = seed.strip().lower()
        if key in label_index:
            resolved.add(label_index[key])
        else:
            unresolved.append(seed)

    if unresolved and comment_index:
        comment_uris = list(comment_index.keys())
        comment_texts = [comment_index[u] for u in comment_uris]
        all_vecs = embed_caller(unresolved + comment_texts)
        if len(all_vecs) == len(unresolved) + len(comment_texts):
            seed_vecs = all_vecs[: len(unresolved)]
            comment_vecs = all_vecs[len(unresolved):]
            for seed_vec in seed_vecs:
                best_uri = None
                best_sim = similarity_threshold
                for uri, cvec in zip(comment_uris, comment_vecs):
                    sim = _cosine(seed_vec, cvec)
                    if sim > best_sim:
                        best_sim = sim
                        best_uri = uri
                if best_uri is not None:
                    resolved.add(best_uri)

    return resolved
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_subgraph_retriever -v`
Expected: PASS, three new tests green.

- [ ] **Step 5: Commit**

```bash
git add GraphRag/subgraph_retriever.py GraphRag/test_subgraph_retriever.py
git commit -m "feat(graphrag): ground seed terms to URIs via label index + comment-embedding fallback"
```

---

## Task 8: Subgraph serialization (triples → prompt-ready text)

**Files:**
- Modify: `GraphRag/subgraph_retriever.py`
- Modify: `GraphRag/test_subgraph_retriever.py`

Output format: one triple per line as `prefix:local prefix:local prefix:local`, plus an appended block of `# comment: <uri short> -> <rdfs:comment text>` lines for URIs whose comments are known. This gives the LLM both structure and natural-language hints.

- [ ] **Step 1: Write the failing test**

Append to `GraphRag/test_subgraph_retriever.py`:

```python
class TestSerializeSubgraph(unittest.TestCase):
    def test_serialize_emits_one_line_per_triple_with_prefixes(self):
        from subgraph_retriever import serialize_subgraph
        from rdflib import URIRef
        from rdflib.namespace import RDFS

        evsla = "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/"
        icm = "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/"
        triples = [
            (URIRef(evsla + "SlaExpectation"), RDFS.subClassOf, URIRef(icm + "PropertyExpectation")),
        ]
        text = serialize_subgraph(triples, comment_index={})

        self.assertIn("evsla:SlaExpectation", text)
        self.assertIn("rdfs:subClassOf", text)
        self.assertIn("icm:PropertyExpectation", text)

    def test_serialize_appends_comment_block_for_known_uris(self):
        from subgraph_retriever import serialize_subgraph
        from rdflib import URIRef
        from rdflib.namespace import RDFS

        evsla = "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/"
        sla_uri = URIRef(evsla + "SlaExpectation")
        triples = [(sla_uri, RDFS.label, sla_uri)]
        text = serialize_subgraph(
            triples,
            comment_index={sla_uri: "A property expectation expressing SLA guarantees."},
        )

        self.assertIn("# comment: evsla:SlaExpectation", text)
        self.assertIn("A property expectation expressing SLA guarantees.", text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_subgraph_retriever -v`
Expected: FAIL — `cannot import name 'serialize_subgraph'`.

- [ ] **Step 3: Implement `serialize_subgraph`**

Add to `GraphRag/subgraph_retriever.py`:

```python
from rdflib.term import Node

KNOWN_PREFIXES: list[tuple[str, str]] = [
    ("evsla", "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/"),
    ("icm", "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/"),
    ("imo", "http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/"),
    ("met", "http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/"),
    ("quan", "http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/"),
    ("fun", "http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/"),
    ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
    ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
    ("skos", "http://www.w3.org/2004/02/skos/core#"),
    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
]


def _shorten(node: Node) -> str:
    s = str(node)
    for prefix, ns in KNOWN_PREFIXES:
        if s.startswith(ns):
            return f"{prefix}:{s[len(ns):]}"
    return f"<{s}>"


def serialize_subgraph(
    triples: list[tuple[Node, Node, Node]],
    comment_index: dict[URIRef, str],
) -> str:
    """Render triples as `s p o` lines plus a comment block for URIs in `comment_index`."""
    triple_lines = [f"{_shorten(s)} {_shorten(p)} {_shorten(o)}" for s, p, o in triples]
    uris_in_subgraph: set[URIRef] = set()
    for s, _, o in triples:
        if isinstance(s, URIRef):
            uris_in_subgraph.add(s)
        if isinstance(o, URIRef):
            uris_in_subgraph.add(o)
    comment_lines: list[str] = []
    for uri in sorted(uris_in_subgraph, key=str):
        if uri in comment_index:
            comment_lines.append(f"# comment: {_shorten(uri)} -> {comment_index[uri]}")
    parts = ["# triples"] + triple_lines
    if comment_lines:
        parts.append("")
        parts.append("# comments")
        parts.extend(comment_lines)
    return "\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_subgraph_retriever -v`
Expected: PASS, two new tests green.

- [ ] **Step 5: Commit**

```bash
git add GraphRag/subgraph_retriever.py GraphRag/test_subgraph_retriever.py
git commit -m "feat(graphrag): serialize subgraph as prefix-shortened triple list with comments"
```

---

## Task 9: End-to-end `build_subgraph_context` orchestrator

**Files:**
- Modify: `GraphRag/subgraph_retriever.py`
- Modify: `GraphRag/test_subgraph_retriever.py`

This is the public API used by `nl_to_tio.py`. It composes: seed extraction → grounding → BFS → serialization. It accepts pre-built indexes and BFS function as parameters so tests don't need real TTL files.

- [ ] **Step 1: Write the failing test**

Append to `GraphRag/test_subgraph_retriever.py`:

```python
class TestBuildSubgraphContext(unittest.TestCase):
    def test_build_subgraph_context_full_pipeline(self):
        from subgraph_retriever import build_subgraph_context
        from rdflib import URIRef
        from rdflib.namespace import RDFS

        evsla = "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/"
        icm = "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/"
        sla_uri = URIRef(evsla + "SlaExpectation")
        prop_uri = URIRef(icm + "PropertyExpectation")

        label_idx = {"sla expectation": sla_uri}
        comment_idx = {sla_uri: "A property expectation for SLA guarantees."}

        def fake_seed_caller(prompt):
            return json.dumps(["sla expectation"])

        def fake_embed_caller(items):
            return [[0.0, 0.0] for _ in items]

        def fake_bfs(seeds, hops):
            return [(sla_uri, RDFS.subClassOf, prop_uri)]

        ctx = build_subgraph_context(
            "確保 SLA 達標",
            label_index=label_idx,
            comment_index=comment_idx,
            seed_caller=fake_seed_caller,
            embed_caller=fake_embed_caller,
            bfs_fn=fake_bfs,
        )

        self.assertIn("evsla:SlaExpectation", ctx)
        self.assertIn("icm:PropertyExpectation", ctx)
        self.assertIn("# comment: evsla:SlaExpectation", ctx)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_subgraph_retriever -v`
Expected: FAIL — `cannot import name 'build_subgraph_context'`.

- [ ] **Step 3: Implement `build_subgraph_context`**

Add to `GraphRag/subgraph_retriever.py`:

```python
def build_subgraph_context(
    nl_intent: str,
    label_index: dict[str, URIRef],
    comment_index: dict[URIRef, str],
    seed_caller: Callable[[str], str],
    embed_caller: Callable[[list[str]], list[list[float]]],
    bfs_fn: Callable[[list[URIRef], int], list[tuple[Node, Node, Node]]],
    hops: int = 2,
) -> str:
    """End-to-end: NL intent → serialized subgraph context string."""
    seeds = extract_seeds(nl_intent, caller=seed_caller)
    grounded = ground_seeds(seeds, label_index, comment_index, embed_caller)
    triples = bfs_fn(list(grounded), hops)
    return serialize_subgraph(triples, comment_index)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_subgraph_retriever -v`
Expected: PASS, new test green.

- [ ] **Step 5: Commit**

```bash
git add GraphRag/subgraph_retriever.py GraphRag/test_subgraph_retriever.py
git commit -m "feat(graphrag): add end-to-end build_subgraph_context orchestrator"
```

---

## Task 10: Wire new retriever into `nl_to_tio.py`

**Files:**
- Modify: `GraphRag/nl_to_tio.py`
- Modify: `GraphRag/test_nl_to_tio.py`

Replace `query_graphrag_local` (subprocess `graphrag query`) with calls to the new retriever. Keep `build_evsla_system_prompt` and `format_few_shot_block` untouched.

- [ ] **Step 1: Write the failing test**

Replace the body of `GraphRag/test_nl_to_tio.py` (keep imports and the path-related tests; remove the `test_graphrag_query_focuses_on_evsla_terms` test that references the now-deleted `build_graphrag_query`). Add a new test class:

```python
class TestSubgraphRetrievalIntegration(unittest.TestCase):
    def test_build_subgraph_context_for_intent_uses_typed_traversal(self):
        # Smoke: real TTL + mocked LLM/embedding callers produce a non-empty
        # subgraph string containing at least one evsla URI.
        from pathlib import Path
        import json

        from ontology_graph import (
            build_comment_index,
            build_label_index,
            load_ontology,
            typed_bfs_subgraph,
        )
        from subgraph_retriever import build_subgraph_context

        ttl_dir = Path(__file__).resolve().parent.parent / "TM Forum Intent Ontology"
        g = load_ontology(ttl_dir)
        label_idx = build_label_index(g)
        comment_idx = build_comment_index(g)

        def fake_seed_caller(prompt):
            return json.dumps(["twamp", "p95 statistic", "sla expectation"])

        def fake_embed_caller(items):
            return [[0.0, 0.0] for _ in items]

        ctx = build_subgraph_context(
            "確保總部至所有分點延遲在95%時間內低於50ms。",
            label_index=label_idx,
            comment_index=comment_idx,
            seed_caller=fake_seed_caller,
            embed_caller=fake_embed_caller,
            bfs_fn=lambda seeds, hops: typed_bfs_subgraph(g, seeds, hops),
        )

        self.assertIn("evsla:", ctx)
        self.assertIn("# triples", ctx)
```

Also delete the lines (in `GraphRag/test_nl_to_tio.py`) for the test method `test_graphrag_query_focuses_on_evsla_terms`, since `build_graphrag_query` is being removed.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest test_nl_to_tio -v`
Expected: FAIL — either `ImportError` from `ontology_graph` if missing or `cannot import name` for new symbols. (If Tasks 1-9 are complete the imports work — in that case this test should PASS; if so move directly to Step 3 to refactor `nl_to_tio.py`.)

- [ ] **Step 3: Refactor `nl_to_tio.py` to use the new retriever**

Edit `GraphRag/nl_to_tio.py`:

1. Remove `subprocess` import.
2. Remove `build_graphrag_query` function (and its export from `evsla_prompt`).
3. Remove `query_graphrag_local` function.
4. Add module-level imports near the existing ones:

```python
from ontology_graph import (
    build_comment_index,
    build_label_index,
    load_ontology,
    typed_bfs_subgraph,
)
from subgraph_retriever import build_subgraph_context

TTL_DIR = Path(__file__).resolve().parent.parent / "TM Forum Intent Ontology"
EMBED_MODEL = "text-embedding-3-small"
```

5. Add real LLM/embedding callers (kept thin so they can be swapped in tests):

```python
def _seed_llm_caller(prompt: str) -> str:
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return (response.choices[0].message.content or "").strip()


def _embed_caller(items: list[str]) -> list[list[float]]:
    if not items:
        return []
    resp = client.embeddings.create(model=EMBED_MODEL, input=items)
    return [d.embedding for d in resp.data]
```

6. In `main()`, before the test-case loop, build indexes once:

```python
print("--- Loading TIO ontology and building indexes ---")
graph = load_ontology(TTL_DIR)
label_idx = build_label_index(graph)
comment_idx = build_comment_index(graph)
```

7. Inside the loop, replace the previous `query_graphrag_local` block with:

```python
tio_context = build_subgraph_context(
    tc["nl_intent"],
    label_index=label_idx,
    comment_index=comment_idx,
    seed_caller=_seed_llm_caller,
    embed_caller=_embed_caller,
    bfs_fn=lambda seeds, hops, g=graph: typed_bfs_subgraph(g, seeds, hops),
)
```

8. In `evsla_prompt.py`, the `build_evsla_graphrag_query` function is no longer imported. Leave it in place (it is harmless, and other tooling may reference it), but remove the `from evsla_prompt import build_evsla_graphrag_query` line in `nl_to_tio.py`.

- [ ] **Step 4: Run all tests in the GraphRag module**

Run: `cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag && python -m unittest discover -v`
Expected: PASS, all tests green (ontology_graph: ~9 tests, subgraph_retriever: ~9 tests, nl_to_tio: path + system-prompt + chat-model + new integration test).

- [ ] **Step 5: Commit**

```bash
git add GraphRag/nl_to_tio.py GraphRag/test_nl_to_tio.py
git commit -m "refactor(graphrag): replace Microsoft graphrag CLI with rdflib typed traversal"
```

---

## Task 11: Smoke-run TC001 end-to-end and inspect output

**Files:**
- Run only (no edits). Output written to `jsonld_outputs/graphrag/TC001.jsonld`.

This task confirms the new pipeline produces JSON-LD that actually contains TIO URIs (`evsla:*`, `icm:*`) — the original failure mode this whole refactor exists to fix.

- [ ] **Step 1: Confirm `.env` has `OPENAI_API_KEY` or `GRAPHRAG_API_KEY`**

Run: `grep -E '^(OPENAI|GRAPHRAG)_API_KEY' /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/.env`
Expected: one matching line. If empty, set the key before continuing.

- [ ] **Step 2: Filter `test_cases_20.json` down to TC001 only for a fast smoke run**

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python -c "import json; data=json.load(open('test_cases_20.json')); json.dump([data[0]], open('/tmp/tc001_only.json','w'), ensure_ascii=False, indent=2)"
```

- [ ] **Step 3: Run the refactored pipeline on TC001**

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python GraphRag/nl_to_tio.py --test-cases /tmp/tc001_only.json
```
Expected: prints "Loading TIO ontology and building indexes" once, then for TC001 prints retrieval + generation logs, ends with "Successfully saved JSON-LD to: .../jsonld_outputs/graphrag/TC001.jsonld".

- [ ] **Step 4: Verify the output uses evsla URIs**

Run: `grep -c 'evsla:' /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/jsonld_outputs/graphrag/TC001.jsonld`
Expected: count >= 5 (was 0 before this refactor).

Also run: `grep -E 'evsla:(latency|p95|twamp|hubToAllSpokes|SlaExpectation|EnterpriseVpnService)' /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/jsonld_outputs/graphrag/TC001.jsonld`
Expected: at least 3 of these specific terms appear (they are all required for TC001 per `test_cases_20.json`).

If the output is empty of `evsla:` URIs, the seed extractor or grounding is likely failing. Debug by adding `print(tio_context)` after the `build_subgraph_context` call in `nl_to_tio.py` to inspect what the LLM is being shown.

- [ ] **Step 5: Run full 20-case batch**

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python GraphRag/nl_to_tio.py
```
Expected: 20 `.jsonld` files refreshed under `jsonld_outputs/graphrag/`.

- [ ] **Step 6: Commit the regenerated outputs**

```bash
git add jsonld_outputs/graphrag/
git commit -m "chore(graphrag): regenerate outputs via typed-traversal pipeline"
```

---

## Out of scope (do not do in this plan)

- 不更動 `LLM-only/`、`KGE/`、`KAG/` 三個目錄
- 不更動 `evaluate_jsonld.py`、`compare_reports.py`（評估指標擴充是另一份 plan 的範圍）
- 不訓 KGE embedding、不寫 KAG logical form 邏輯（各自獨立 plan）
- 不刪 `GraphRag/cache/`、`input/`、`output/`、`logs/`、`settings.yaml`、`temp_init/`（Microsoft GraphRAG 殘留物，留作對照與審計）
- 不修改 ontology TTL 檔
- 不擴充 `test_cases_20.json`

## Self-Review Notes

- Spec coverage: §4.1（招牌機制）、§4.2（與舊版差別）、§4.3（設計）的四個步驟（graph build / 三 index / 檢索流程 / prompt）都有對應 Task。§4.4 與 §4.5 是預期假設與指標，由 Task 11 的 grep 與後續 `compare_reports.py` 驗證。
- Placeholder scan: 所有 step 都含實際 code、實際指令、預期輸出。沒有 "TBD" / "implement later" / "similar to Task N"。
- Type consistency: `build_subgraph_context` 在 Task 9 定義的參數簽名（`label_index`, `comment_index`, `seed_caller`, `embed_caller`, `bfs_fn`, `hops`）與 Task 10 在 `nl_to_tio.py` 呼叫端使用的關鍵字參數一致。`typed_bfs_subgraph` 的簽名 `(graph, seeds, hops)` 在 Task 5 與 Task 10 一致。`ground_seeds` 的 `similarity_threshold` 預設值 0.6 與 Task 7 測試的 0.5/0.9 並無衝突。
