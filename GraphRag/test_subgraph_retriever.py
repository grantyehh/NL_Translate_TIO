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
    assert "ComparisonOperator:" in ctx
