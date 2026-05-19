from __future__ import annotations

from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDFS, SKOS

# Several TIO v3.6.0 TTL files omit prefix declarations that they reference.
# Inject the missing bindings when they are absent so rdflib can parse them.
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


def load_ontology(ttl_dir: Path) -> Graph:
    """Load and merge all .ttl files in ttl_dir into a single rdflib Graph."""
    g = Graph()
    for ttl_path in sorted(Path(ttl_dir).glob("*.ttl")):
        g.parse(data=_prepend_missing_tio_prefixes(ttl_path), format="turtle")
    return g
