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
    relations, reached = traverse_connective(graph, [URIRef(EVSLA + "latency")])
    pred_uris = {p for _, p, _ in relations}
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
    assert "MeasurementMethod" not in vocab


def test_ttl_encodes_conventions():
    from rdflib.namespace import RDFS
    g = load_ontology(TTL_DIR)
    E = lambda n: URIRef(EVSLA + n)
    dmm = E("defaultMeasurementMethod")
    assert (E("latency"), dmm, E("twamp")) in g
    assert (E("packetLoss"), dmm, E("twamp")) in g
    assert (E("guaranteedBandwidth"), dmm, E("activeMeasurement")) in g
    assert any(g.objects(E("fiveMinuteWindow"), E("isDefaultTimeWindow")))
    zh_one = [str(o) for o in g.objects(E("oneHourWindow"), RDFS.label)
              if getattr(o, "language", None) == "zh"]
    zh_month = [str(o) for o in g.objects(E("monthlySlaWindow"), RDFS.label)
                if getattr(o, "language", None) == "zh"]
    assert any("每小時" in s for s in zh_one)
    assert any("月度" in s for s in zh_month)
