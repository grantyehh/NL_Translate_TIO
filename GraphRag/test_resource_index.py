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
    assert idx["evsla:SlaExpectation"].role_class is None

def test_full_iri_and_labels_preserved():
    resources = build_resource_index(load_ontology(TTL_DIR))
    idx = _by_curie(resources)
    assert idx["evsla:latency"].uri == (
        "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/latency"
    )
    assert any("latency" in lbl.lower() for lbl in idx["evsla:latency"].labels)
    assert "TWAMP" in idx["evsla:twamp"].alt_labels
