import json
import unittest

from rdflib import URIRef

from subgraph_retriever import extract_seeds, ground_seeds


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


if __name__ == "__main__":
    unittest.main()
