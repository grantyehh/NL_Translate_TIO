from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, SKOS
from rdflib.term import Node

# Several TIO v3.6.0 TTL files omit prefix declarations that they reference.
# Inject the missing bindings when they are absent so rdflib can parse them.
TRAVERSAL_PREDICATES = (
    RDFS.subClassOf,
    RDFS.subPropertyOf,
    RDF.type,
    RDFS.domain,
    RDFS.range,
)

_MISSING_PREFIXES = {
    "icm": "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/",
    "imo": "http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/",
}


def _prepend_missing_tio_prefixes(ttl_path: Path) -> str:
    """Pre-inject the two TIO v3.6.0 prefix declarations (icm:, imo:)
    that five upstream TTL files reference but omit."""
    content = ttl_path.read_text(encoding="utf-8")
    injection = "".join(
        f"@prefix {pfx}: <{uri}> .\n"
        for pfx, uri in _MISSING_PREFIXES.items()
        if f"@prefix {pfx}:" not in content
    )
    return injection + content


def build_label_index(graph: Graph) -> dict[str, URIRef]:
    """Map normalised label string (lowercase, stripped) -> URI.

    Sources: rdfs:label and skos:altLabel, treated equally (no predicate
    priority). If multiple URIs share a normalised label, the
    lexicographically smallest URI wins (deterministic).
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


def build_type_index(graph: Graph) -> dict[URIRef, set[URIRef]]:
    """Map class URI → set of URIs that are rdf:type of that class."""
    index: dict[URIRef, set[URIRef]] = defaultdict(set)
    for subject, _, cls in graph.triples((None, RDF.type, None)):
        if isinstance(subject, URIRef) and isinstance(cls, URIRef):
            index[cls].add(subject)
    return dict(index)


def build_comment_index(graph: Graph) -> dict[URIRef, str]:
    """Map URI → its first rdfs:comment string. Skips URIs with no comment."""
    index: dict[URIRef, str] = {}
    for subject, _, literal in graph.triples((None, RDFS.comment, None)):
        if isinstance(subject, URIRef) and subject not in index:
            index[subject] = str(literal)
    return index


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


def load_ontology(ttl_dir: Path) -> Graph:
    """Load and merge all .ttl files in ttl_dir into a single rdflib Graph."""
    g = Graph()
    for ttl_path in sorted(Path(ttl_dir).glob("*.ttl")):
        g.parse(data=_prepend_missing_tio_prefixes(ttl_path), format="turtle")
    return g
