"""
Extract RDF triples from TIO TTL files for knowledge graph embedding training.
"""

from __future__ import annotations

import sys
from pathlib import Path

from rdflib import Graph, URIRef, BNode, RDFS

# Allow `python -m kge.train` from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evaluate_ttl import ONTOLOGY_PREFIX_PREAMBLE  # noqa: E402

TIO_BASE = "http://tio.models.tmforum.org/tio/v3.6.0/"

# Skip metadata predicates that add noise / external IRIs for structural KGE
SKIP_PREDICATE_PREFIXES = (
    "http://purl.org/dc/terms/",
)

# RDFS has lowercase 'comment'; files also use rdfs:Comment (non-standard)
RDFS_COMMENT_ALT = URIRef("http://www.w3.org/2000/01/rdf-schema#Comment")


def _is_tio_uri(uri: str) -> bool:
    return uri.startswith(TIO_BASE)


def _should_skip_predicate(p: str) -> bool:
    return any(p.startswith(pref) for pref in SKIP_PREDICATE_PREFIXES)


def load_merged_ontology_graph(ontology_dir: Path | None = None) -> Graph:
    """Load all *.ttl under TM Forum Intent Ontology with a shared prefix preamble."""
    g = Graph()
    base = ontology_dir or (_PROJECT_ROOT / "TM Forum Intent Ontology")
    for path in sorted(base.glob("*.ttl")):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        g.parse(data=ONTOLOGY_PREFIX_PREAMBLE + content, format="turtle")
    return g


def extract_triples_for_kge(ontology_dir: Path | None = None) -> list[tuple[str, str, str]]:
    """
    Return (h, r, t) string triples for PyKEEN.
    Keep only URI-to-URI triples so entity IDs stay as stable ontology IRIs.
    """
    g = load_merged_ontology_graph(ontology_dir)
    out: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for s, p, o in g:
        if not isinstance(s, URIRef):
            continue
        hs = str(s)
        if not _is_tio_uri(hs):
            continue
        ps = str(p)
        if _should_skip_predicate(ps):
            continue

        if isinstance(o, BNode) or not isinstance(o, URIRef):
            continue
        ts = str(o)

        key = (hs, ps, ts)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)

    return out


def entity_text_description(g: Graph, uri: str) -> str:
    """Label + comments for embedding and prompt display."""
    s = URIRef(uri)
    parts: list[str] = []
    for pred in (RDFS.label, RDFS.comment, RDFS_COMMENT_ALT):
        for lit in g.objects(s, pred):
            parts.append(str(lit))
    if not parts:
        return uri.rsplit("/", 1)[-1].replace("#", ":")
    return " ".join(parts)


def build_entity_descriptions(
    entity_ids: list[str], ontology_dir: Path | None = None
) -> dict[str, str]:
    """Map entity IRI -> text for text embedding."""
    g = load_merged_ontology_graph(ontology_dir)
    return {eid: entity_text_description(g, eid) for eid in entity_ids}
