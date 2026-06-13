import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


os.environ.setdefault("OPENAI_API_KEY", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import nl_to_tio  # noqa: E402


class TestGraphRagPaths(unittest.TestCase):
    def test_default_test_cases_path_points_to_repo_root_shared_file(self) -> None:
        root = Path("/tmp/example/CHT/GraphRag")
        expected = Path("/tmp/example/CHT/test_cases_20.json").resolve()
        self.assertEqual(nl_to_tio.default_test_cases_path(root), expected)

    def test_default_few_shot_path_points_to_repo_root_shared_file(self) -> None:
        root = Path("/tmp/example/CHT/GraphRag")
        expected = Path("/tmp/example/CHT/few_shot_samples.json").resolve()
        self.assertEqual(nl_to_tio.default_few_shot_path(root), expected)

    def test_format_few_shot_block_uses_json_ld_examples(self) -> None:
        examples = [
            {
                "pattern": "property_expectation",
                "nl_intent": "確保視訊會議流量的延遲低於 20ms。",
                "jsonld": {"@type": "Intent", "id": "intent-video-conf-001"},
            }
        ]

        block = nl_to_tio.format_few_shot_block(examples)

        self.assertIn("JSON-LD:", block)
        self.assertIn('"@type": "Intent"', block)
        self.assertNotIn("Turtle:", block)

    def test_output_path_uses_jsonld_outputs_and_extension(self) -> None:
        root = Path("/tmp/example/CHT/GraphRag")
        expected = Path("/tmp/example/CHT/jsonld_outputs/graphrag/TC001.jsonld")
        self.assertEqual(nl_to_tio.output_path_for_case(root, "TC001"), expected)

    def test_token_usage_path_uses_phase1_token_usage_directory(self) -> None:
        root = Path("/tmp/example/CHT/GraphRag")
        expected = Path("/tmp/example/CHT/phase1/token_usage/token_usage_graphrag.json")
        self.assertEqual(nl_to_tio.token_usage_path(root), expected)

    def test_system_prompt_requires_json_ld_not_turtle(self) -> None:
        prompt = nl_to_tio.build_system_prompt("TC001")

        self.assertIn("JSON-LD", prompt)
        self.assertIn("intentExpectation", prompt)
        self.assertNotIn("僅輸出完整、可解析的 Turtle", prompt)

    def test_system_prompt_requires_enterprise_vpn_sla_ontology_terms(self) -> None:
        prompt = nl_to_tio.build_system_prompt("TC001")

        self.assertIn("evsla:EnterpriseVpnSlaIntent", prompt)
        self.assertIn("evsla:EnterpriseVpnService", prompt)
        self.assertIn("evsla:HubAndSpokeTopology", prompt)
        self.assertIn("latency -> evsla:latency", prompt)
        self.assertIn("95% -> evsla:p95", prompt)
        self.assertIn("所有分點 / 各Spoke -> evsla:hubToAllSpokes", prompt)
        self.assertNotIn("DeliveryExpectation", prompt)

    def test_chat_model_uses_gpt_5_4(self) -> None:
        self.assertEqual(nl_to_tio.CHAT_MODEL, "gpt-5.4")

    def test_normalize_jsonld_fills_missing_expectation_description(self) -> None:
        raw = """{
  "@type": "Intent",
  "id": "intent-tc002",
  "name": "Enterprise VPN Hub-Spoke SLA Intent",
  "description": "Assure packet loss below 0.1%.",
  "intentExpectation": [
    {
      "id": "exp-tc002-packet-loss",
      "name": "Hub-to-Spoke Packet Loss SLA Expectation",
      "@type": "PropertyExpectation"
    }
  ]
}"""

        normalized = nl_to_tio.normalize_jsonld_output(raw)

        self.assertIn('"description": "Hub-to-Spoke Packet Loss SLA Expectation"', normalized)

    def test_generate_jsonld_code_records_token_usage(self) -> None:
        completion = Mock()
        completion.choices = [Mock(message=Mock(content='{"@context": {}}'))]
        completion.usage = Mock(prompt_tokens=20, completion_tokens=10, total_tokens=30)

        with tempfile.TemporaryDirectory() as tmp:
            usage_path = Path(tmp) / "token_usage_graphrag.json"
            with patch.object(
                nl_to_tio.client.chat.completions,
                "create",
                return_value=completion,
            ), patch.object(nl_to_tio, "token_usage_path", return_value=usage_path):
                result = nl_to_tio.generate_jsonld_code(
                    "確保延遲低於 50ms",
                    "context",
                    "TC001",
                    "",
                )

            self.assertEqual(result, '{"@context": {}}')
            rows = json.loads(usage_path.read_text(encoding="utf-8"))
            self.assertEqual(rows[0]["experiment"], "graphrag")
            self.assertEqual(rows[0]["stage"], "jsonld_generation")
            self.assertEqual(rows[0]["total_tokens"], 30)


class TestSubgraphRetrievalIntegration(unittest.TestCase):
    def test_build_subgraph_context_for_intent_uses_typed_traversal(self):
        # Smoke: real TTL + mocked LLM/embedding callers produce a non-empty
        # subgraph string containing at least one evsla URI.
        from pathlib import Path
        import json

        from ontology_graph import (
            build_comment_index,
            build_label_index,
            load_ontology,
            typed_bfs_subgraph,
        )
        from subgraph_retriever import build_subgraph_context

        ttl_dir = Path(__file__).resolve().parent.parent / "TM Forum Intent Ontology"
        g = load_ontology(ttl_dir)
        label_idx = build_label_index(g)
        comment_idx = build_comment_index(g)

        def fake_seed_caller(prompt):
            return json.dumps(["twamp", "p95 statistic", "sla expectation"])

        def fake_embed_caller(items):
            return [[0.0, 0.0] for _ in items]

        ctx = build_subgraph_context(
            "確保總部至所有分點延遲在95%時間內低於50ms。",
            label_index=label_idx,
            comment_index=comment_idx,
            seed_caller=fake_seed_caller,
            embed_caller=fake_embed_caller,
            bfs_fn=lambda seeds, hops: typed_bfs_subgraph(g, seeds, hops),
        )

        self.assertIn("evsla:", ctx)
        self.assertIn("# triples", ctx)


if __name__ == "__main__":
    unittest.main()
