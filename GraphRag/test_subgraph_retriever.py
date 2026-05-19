import json
import unittest

from rdflib import URIRef
from rdflib.namespace import RDFS

from subgraph_retriever import build_subgraph_context, extract_seeds, ground_seeds, serialize_subgraph


class TestExtractSeeds(unittest.TestCase):
    def test_extract_seeds_parses_json_array_from_llm(self):
        def fake_caller(prompt: str) -> str:
            return json.dumps(["latency", "p95", "TWAMP", "hub to all spokes"])

        seeds = extract_seeds("確保總部至所有分點延遲95%時間內低於50ms", caller=fake_caller)

        self.assertEqual(seeds, ["latency", "p95", "TWAMP", "hub to all spokes"])

    def test_extract_seeds_strips_code_fences(self):
        def fake_caller(prompt: str) -> str:
            return '```json\n["latency", "p95"]\n```'

        seeds = extract_seeds("dummy", caller=fake_caller)

        self.assertEqual(seeds, ["latency", "p95"])

    def test_extract_seeds_returns_empty_on_invalid_json(self):
        def fake_caller(prompt: str) -> str:
            return "not json"

        seeds = extract_seeds("dummy", caller=fake_caller)

        self.assertEqual(seeds, [])


class TestGroundSeeds(unittest.TestCase):
    def test_ground_seeds_uses_label_index_when_available(self):
        label_idx = {
            "twamp": URIRef("http://example.org/evsla/twamp"),
            "p95 statistic": URIRef("http://example.org/evsla/p95"),
        }

        grounded = ground_seeds(
            ["TWAMP", "p95 statistic"],
            label_index=label_idx,
            comment_index={},
            embed_caller=lambda items: [],
        )

        self.assertIn(URIRef("http://example.org/evsla/twamp"), grounded)
        self.assertIn(URIRef("http://example.org/evsla/p95"), grounded)

    def test_ground_seeds_falls_back_to_comment_similarity(self):
        uri = URIRef("http://example.org/evsla/hubToAllSpokes")
        comment_idx = {uri: "The SLA metric is evaluated from the hub site to all spoke sites."}

        # Embed: returns identical vector for seed and comment → cosine = 1
        def fake_embed(items):
            return [[1.0, 0.0] for _ in items]

        grounded = ground_seeds(
            ["hub to all spokes"],
            label_index={},
            comment_index=comment_idx,
            embed_caller=fake_embed,
            similarity_threshold=0.5,
        )

        self.assertIn(uri, grounded)

    def test_ground_seeds_skips_when_no_match(self):
        def fake_embed(items):
            # First item (seed) is [1, 0]; comment items are orthogonal [0, 1]
            return [[1.0, 0.0]] + [[0.0, 1.0] for _ in items[1:]]

        grounded = ground_seeds(
            ["nonexistent term"],
            label_index={},
            comment_index={URIRef("http://example.org/x"): "completely unrelated"},
            embed_caller=fake_embed,
            similarity_threshold=0.9,
        )

        self.assertEqual(grounded, set())


class TestSerializeSubgraph(unittest.TestCase):
    def test_serialize_emits_one_line_per_triple_with_prefixes(self):
        evsla = "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/"
        icm = "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/"
        triples = [
            (URIRef(evsla + "SlaExpectation"), RDFS.subClassOf, URIRef(icm + "PropertyExpectation")),
        ]
        text = serialize_subgraph(triples, comment_index={})

        self.assertIn("evsla:SlaExpectation", text)
        self.assertIn("rdfs:subClassOf", text)
        self.assertIn("icm:PropertyExpectation", text)

    def test_serialize_appends_comment_block_for_known_uris(self):
        evsla = "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/"
        sla_uri = URIRef(evsla + "SlaExpectation")
        triples = [(sla_uri, RDFS.label, sla_uri)]
        text = serialize_subgraph(
            triples,
            comment_index={sla_uri: "A property expectation expressing SLA guarantees."},
        )

        self.assertIn("# comment: evsla:SlaExpectation", text)
        self.assertIn("A property expectation expressing SLA guarantees.", text)


class TestBuildSubgraphContext(unittest.TestCase):
    def test_build_subgraph_context_full_pipeline(self):
        evsla = "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/"
        icm = "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/"
        sla_uri = URIRef(evsla + "SlaExpectation")
        prop_uri = URIRef(icm + "PropertyExpectation")

        label_idx = {"sla expectation": sla_uri}
        comment_idx = {sla_uri: "A property expectation for SLA guarantees."}

        def fake_seed_caller(prompt):
            return json.dumps(["sla expectation"])

        def fake_embed_caller(items):
            return [[0.0, 0.0] for _ in items]

        def fake_bfs(seeds, hops):
            return [(sla_uri, RDFS.subClassOf, prop_uri)]

        ctx = build_subgraph_context(
            "確保 SLA 達標",
            label_index=label_idx,
            comment_index=comment_idx,
            seed_caller=fake_seed_caller,
            embed_caller=fake_embed_caller,
            bfs_fn=fake_bfs,
        )

        self.assertIn("evsla:SlaExpectation", ctx)
        self.assertIn("icm:PropertyExpectation", ctx)
        self.assertIn("# comment: evsla:SlaExpectation", ctx)


if __name__ == "__main__":
    unittest.main()
