import json
import unittest

from subgraph_retriever import extract_seeds


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


if __name__ == "__main__":
    unittest.main()
