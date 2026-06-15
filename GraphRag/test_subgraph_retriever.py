import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ontology_graph import load_ontology
from resource_index import build_resource_index, OntologyResource
from subgraph_retriever import ground_query, build_retrieval_context, _lexical

TTL_DIR = Path(__file__).resolve().parent.parent / "TM Forum Intent Ontology"

def test_short_alias_does_not_falsely_ground():
    # a single-character curie-local name must not perfectly match an unrelated query
    short = OntologyResource(uri="x", curie="mf:c", labels=(), alt_labels=(),
                             comment="", role="instance", rdf_types=(), role_class=None)
    assert _lexical("latency packet loss", short) < 1.0
    latency = OntologyResource(uri="y", curie="evsla:latency", labels=("Latency Metric Property",),
                               alt_labels=(), comment="", role="property", rdf_types=(), role_class="Metric")
    assert _lexical("latency", latency) == 1.0


def test_exact_label_grounds_to_correct_uri():
    resources = build_resource_index(load_ontology(TTL_DIR))
    matches = ground_query("latency", resources, embeddings=None, query_vector=None, top_k=5)
    assert any(m.curie == "evsla:latency" for m in matches)

def test_context_is_self_contained_and_role_scoped():
    graph = load_ontology(TTL_DIR)
    resources = build_resource_index(graph)
    ctx = build_retrieval_context(
        "latency", graph=graph, resources=resources, embeddings=None, query_vector=None,
    )
    assert "evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/>" in ctx
    assert "evsla:latency" in ctx
    assert "Statistic:" in ctx and "Scope:" in ctx
    assert "ComparisonOperator:" in ctx
    # query-scoping: a latency-only query must NOT pull topology wiring
    assert "hasSpoke" not in ctx
    assert "HubSite" not in ctx
