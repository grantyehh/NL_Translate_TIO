import json
from pathlib import Path

ALLOWED = {
    "metric": {"evsla:latency", "evsla:packetLoss", "evsla:guaranteedBandwidth"},
    "statistic": {"evsla:p95", "evsla:p99", "evsla:average", "evsla:maximum", "evsla:minimum"},
    "scope": {"evsla:hubToAllSpokes", "evsla:perSpoke", "evsla:specificSpoke"},
    "measurement_method": {"evsla:activeMeasurement", "evsla:twamp"},
    "time_window": {"evsla:fiveMinuteWindow", "evsla:oneHourWindow", "evsla:monthlySlaWindow"},
}

def test_40_cases_present_and_valid():
    data = json.loads(Path("test_cases_40.json").read_text(encoding="utf-8"))
    ids = [c["id"] for c in data]
    assert ids == [f"TC{n:03d}" for n in range(1, 41)]
    for c in data:
        raw = json.dumps(c, ensure_ascii=False)
        assert "jitter" not in raw.lower()
        for pm in c["performance_metrics"]:
            assert pm["ontology_term"] in ALLOWED["metric"]
            assert pm["statistic"] in ALLOWED["statistic"]
            assert pm["scope"] in ALLOWED["scope"]
            assert pm["measurement_method"] in ALLOWED["measurement_method"]
            assert pm["time_window"] in ALLOWED["time_window"]

def test_new_dimensions_covered():
    data = json.loads(Path("test_cases_40.json").read_text(encoding="utf-8"))
    new = [c for c in data if int(c["id"][2:]) >= 21]
    scopes = {pm["scope"] for c in new for pm in c["performance_metrics"]}
    assert "evsla:perSpoke" in scopes
    assert any(len(c["performance_metrics"]) >= 2 for c in new)
    assert any(len(c["scope"]["spokes"]) >= 5 for c in new)
