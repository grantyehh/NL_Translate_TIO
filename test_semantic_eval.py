import unittest

from rdflib import Graph

from semantic_eval import (
    expand, extract_bindings, score_semantics,
    OPERATOR_FN, WEIGHTS, QUAN, EVSLA,
)

GOOD_TTL = """
@prefix icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .
@prefix quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex:    <http://example.org/tio-instance/tc001/> .
ex:intent a icm:Intent, evsla:EnterpriseVpnSlaIntent ;
  icm:intentElements ex:exp-latency, ex:topology .
ex:tenant a evsla:Tenant ; rdfs:label "星河銀行"@zh .
ex:exp-latency a icm:PropertyExpectation, evsla:SlaExpectation ; icm:target ex:tgt-latency .
ex:tgt-latency a icm:Target ;
  evsla:hasMetric evsla:latency ;
  evsla:hasThreshold [ a quan:Quantity ; rdf:value 50 ; quan:unit "ms" ] ;
  evsla:hasStatistic evsla:p95 ; evsla:hasScope evsla:hubToAllSpokes ;
  evsla:hasMeasurementMethod evsla:twamp ; evsla:hasTimeWindow evsla:fiveMinuteWindow .
ex:topology a icm:Context, evsla:HubAndSpokeTopology ;
  evsla:hasHub [ a evsla:HubSite ; rdfs:label "總部"@zh ] ;
  evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label "所有分點"@zh ] .
"""

GOLD_TC001 = {
    "tenant": "星河銀行",
    "performance_metrics": [{
        "operator": "LESS_THAN", "threshold": {"value": 50, "unit": "ms"},
        "ontology_term": "evsla:latency", "statistic": "evsla:p95",
        "scope": "evsla:hubToAllSpokes", "measurement_method": "evsla:twamp",
        "time_window": "evsla:fiveMinuteWindow",
    }],
}


class TestScaffold(unittest.TestCase):
    def test_expand_curie(self):
        self.assertEqual(str(expand("evsla:latency")),
            "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/latency")

    def test_operator_map(self):
        self.assertEqual(OPERATOR_FN["LESS_THAN"], QUAN.smaller)
        self.assertEqual(OPERATOR_FN["GREATER_THAN_OR_EQUAL"], QUAN.atLeast)

    def test_weights_keys(self):
        self.assertEqual(set(WEIGHTS), {
            "metric", "threshold", "statistic", "scope", "measurement_method",
            "time_window", "operator", "tenant", "topology", "contract", "precision"})


class TestBindings(unittest.TestCase):
    def test_extract_one_binding(self):
        g = Graph(); g.parse(data=GOOD_TTL, format="turtle")
        b = extract_bindings(g)
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0]["metric"], EVSLA.latency)
        self.assertEqual(b[0]["scope"], EVSLA.hubToAllSpokes)


class TestScore(unittest.TestCase):
    def test_correct_graph_scores_high(self):
        g = Graph(); g.parse(data=GOOD_TTL, format="turtle")
        r = score_semantics(g, GOLD_TC001)
        d = r["dimensions"]
        self.assertEqual(d["metric"], 1.0)
        self.assertEqual(d["threshold"], 1.0)
        self.assertEqual(d["statistic"], 1.0)
        self.assertEqual(d["scope"], 1.0)
        self.assertEqual(d["tenant"], 1.0)
        self.assertEqual(d["topology"], 1.0)
        self.assertEqual(d["contract"], 1.0)
        self.assertEqual(d["operator"], 0.0)            # no quan:smaller emitted
        self.assertEqual(r["precision"]["hallucination_count"], 0)
        self.assertGreater(r["composite"], 0.85)

    def test_wrong_scope_and_value_penalised(self):
        bad = GOOD_TTL.replace("evsla:hubToAllSpokes", "evsla:specificSpoke") \
                      .replace("rdf:value 50", "rdf:value 999")
        g = Graph(); g.parse(data=bad, format="turtle")
        d = score_semantics(g, GOLD_TC001)["dimensions"]
        self.assertEqual(d["scope"], 0.0)
        self.assertEqual(d["threshold"], 0.0)
        self.assertEqual(d["metric"], 1.0)

    def test_hallucinated_extra_metric(self):
        extra = GOOD_TTL.replace(
            "icm:intentElements ex:exp-latency, ex:topology .",
            "icm:intentElements ex:exp-latency, ex:exp-bw, ex:topology .") + """
ex:exp-bw a icm:PropertyExpectation, evsla:SlaExpectation ; icm:target ex:tgt-bw .
ex:tgt-bw a icm:Target ; evsla:hasMetric evsla:guaranteedBandwidth .
"""
        g = Graph(); g.parse(data=extra, format="turtle")
        r = score_semantics(g, GOLD_TC001)
        self.assertEqual(r["precision"]["hallucination_count"], 1)
        self.assertLess(r["dimensions"]["precision"], 1.0)


OP_TTL = """
@prefix icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .
@prefix quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .
@prefix log:   <http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/> .
@prefix met:   <http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex:    <http://example.org/tio-instance/tc001/> .
ex:intent a icm:Intent, evsla:EnterpriseVpnSlaIntent ;
  icm:intentElements ex:exp-latency, ex:topology, ex:cond-latency .
ex:tenant a evsla:Tenant ; rdfs:label "星河銀行"@zh .
ex:cond-latency a log:Condition ;
  quan:smaller ( ex:obs-latency-value ex:thr-latency ) .
ex:obs-latency a met:Observation ; met:observedMetric evsla:latency .
ex:obs-latency-value a quan:Quantity ; met:observedValue ( ex:obs-latency ) .
ex:exp-latency a icm:PropertyExpectation, evsla:SlaExpectation ; icm:target ex:tgt-latency .
ex:tgt-latency a icm:Target ;
  evsla:hasMetric evsla:latency ;
  evsla:hasThreshold ex:thr-latency ;
  icm:valuesOfTargetProperty ex:thr-latency ;
  evsla:hasStatistic evsla:p95 ; evsla:hasScope evsla:hubToAllSpokes ;
  evsla:hasMeasurementMethod evsla:twamp ; evsla:hasTimeWindow evsla:fiveMinuteWindow .
ex:thr-latency a quan:Quantity ; rdf:value 50 ; quan:unit "ms" .
ex:topology a icm:Context, evsla:HubAndSpokeTopology ;
  evsla:hasHub [ a evsla:HubSite ; rdfs:label "總部"@zh ] ;
  evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label "所有分點"@zh ] .
"""


class TestOperator(unittest.TestCase):
    def test_operator_correct_function_bound_to_threshold(self):
        g = Graph(); g.parse(data=OP_TTL, format="turtle")
        r = score_semantics(g, GOLD_TC001)["dimensions"]
        self.assertEqual(r["operator"], 1.0)
        self.assertEqual(r["threshold"], 1.0)   # still read from the named threshold node

    def test_operator_wrong_function_scores_zero(self):
        g = Graph(); g.parse(data=OP_TTL.replace("quan:smaller", "quan:atLeast"), format="turtle")
        self.assertEqual(score_semantics(g, GOLD_TC001)["dimensions"]["operator"], 0.0)

    def test_operator_absent_scores_zero(self):
        g = Graph(); g.parse(data=GOOD_TTL, format="turtle")
        self.assertEqual(score_semantics(g, GOLD_TC001)["dimensions"]["operator"], 0.0)


if __name__ == "__main__":
    unittest.main()
