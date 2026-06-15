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
    assert "MeasurementMethod" not in ctx

def test_guard_drops_lowest_when_over_budget():
    items = [("a", 100), ("b", 100), ("c", 100)]
    kept, dropped = guard_tokens(items, budget=250)
    assert [t for t, _ in kept] == ["a", "b"]
    assert [t for t, _ in dropped] == ["c"]
