import os
import sys
import unittest
from pathlib import Path


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

    def test_graphrag_query_focuses_on_evsla_terms(self) -> None:
        query = nl_to_tio.build_graphrag_query("確保星河銀行總部至所有分點之延遲低於50ms。")

        self.assertIn("TM Forum Intent Ontology v3.6.0", query)
        self.assertIn("EnterpriseVpnSlaOntology", query)
        self.assertIn("evsla:EnterpriseVpnSlaIntent", query)
        self.assertIn("evsla:latency", query)
        self.assertNotIn("5G", query)
        self.assertNotIn("QoS", query)
        self.assertNotIn("icm:DeliveryExpectation", query)

    def test_chat_model_uses_gpt_5_4(self) -> None:
        self.assertEqual(nl_to_tio.CHAT_MODEL, "gpt-5.4")


if __name__ == "__main__":
    unittest.main()
