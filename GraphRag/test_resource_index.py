import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ontology_graph import load_ontology
from resource_index import build_resource_index, to_curie, TIO

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


def test_to_curie_known_namespaces():
    assert to_curie(TIO + "EnterpriseVpnSlaOntology/latency") == "evsla:latency"
    assert to_curie(TIO + "QuantityOntology/smaller") == "quan:smaller"

def test_metric_role_is_evsla_scoped():
    resources = build_resource_index(load_ontology(TTL_DIR))
    metric_curies = [r.curie for r in resources if r.role_class == "Metric"]
    assert set(metric_curies) == {"evsla:latency", "evsla:packetLoss", "evsla:guaranteedBandwidth"}

import json
import numpy as np

def test_check_mode_reports_without_api(tmp_path, capsys):
    from build_index import main as build_main
    rc = build_main(["--check", "--output-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "missing" in out.lower() or "stale" in out.lower() or "ok" in out.lower()
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


def test_class_role_covers_tenant_and_topology():
    from resource_index import CLASS_ROLE
    from rdflib import URIRef
    ns = TIO + "EnterpriseVpnSlaOntology/"
    for cls, role in [("Tenant", "Tenant"), ("HubSite", "HubSite"),
                      ("SpokeSite", "SpokeSite"),
                      ("HubAndSpokeTopology", "HubAndSpokeTopology")]:
        assert CLASS_ROLE.get(URIRef(ns + cls)) == role
