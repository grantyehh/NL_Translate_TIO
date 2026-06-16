import unittest

from evsla_prompt import build_evsla_system_prompt


class TestWeak(unittest.TestCase):
    def test_weak_drops_domain_knowledge(self):
        w = build_evsla_system_prompt("TC001", retrieval_mode="GraphRAG", weak_prompt=True)
        for banned in ["evsla:latency", "evsla:hasMetric", "quan:smaller", "Metric mappings",
                       "Graph structure", "hubToAllSpokes", "p95"]:
            self.assertNotIn(banned, w)
        self.assertIn("Turtle", w)        # output-format kept
        self.assertIn("tc001", w)         # ex: namespace kept
        self.assertIn("GraphRAG", w)      # retrieval note kept

    def test_strong_unchanged(self):
        s = build_evsla_system_prompt("TC001")
        self.assertIn("evsla:hasMetric", s)
        self.assertIn("quan:smaller", s)


class TestStructureOnly(unittest.TestCase):
    def test_requires_tenant_and_typed_topology(self):
        p = build_evsla_system_prompt("TC021", retrieval_mode="GraphRAG",
                                      profile="structure_only")
        low = p.lower()
        self.assertIn("tenant", low)        # tenant binding required
        self.assertIn("rdfs:label", p)      # label carried from NL
        self.assertIn("hub", low)
        self.assertIn("spoke", low)
        # structure-only contract preserved: no leaked EVSLA vocabulary IRIs
        self.assertNotIn("evsla:twamp", p)
        self.assertNotIn("evsla:fiveMinuteWindow", p)


if __name__ == "__main__":
    unittest.main()
