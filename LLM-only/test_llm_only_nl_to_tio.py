import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Load LLM-only nl_to_tio.py with a unique module name to avoid collision
# with GraphRag/nl_to_tio.py when pytest collects both directories together.
_MODULE_PATH = Path(__file__).resolve().parent / "nl_to_tio.py"
_spec = importlib.util.spec_from_file_location("llm_only_nl_to_tio", _MODULE_PATH)
nl_to_tio = importlib.util.module_from_spec(_spec)
sys.modules["llm_only_nl_to_tio"] = nl_to_tio
_spec.loader.exec_module(nl_to_tio)


class TestLlmOnlyPaths(unittest.TestCase):
    def setUp(self):
        # Reset profile to default between tests
        nl_to_tio.PROFILE = "strong"
        nl_to_tio.WEAK = False

    def test_default_test_cases_path_points_to_repo_root_shared_file(self) -> None:
        root = Path("/tmp/example/CHT/LLM-only")
        expected = Path("/tmp/example/CHT/test_cases_20.json").resolve()
        self.assertEqual(nl_to_tio.default_test_cases_path(root), expected)

    def test_default_few_shot_path_points_to_repo_root_shared_file(self) -> None:
        root = Path("/tmp/example/CHT/LLM-only")
        expected = Path("/tmp/example/CHT/few_shot_samples.json").resolve()
        self.assertEqual(nl_to_tio.default_few_shot_path(root), expected)

    def test_format_few_shot_block_uses_turtle_examples(self) -> None:
        examples = [{"pattern": "p", "nl_intent": "x",
                     "turtle": "ex:i a icm:Intent ."}]
        block = nl_to_tio.format_few_shot_block(examples)
        self.assertIn("Turtle:", block)
        self.assertIn("a icm:Intent", block)
        self.assertNotIn("JSON-LD:", block)

    def test_output_path_uses_tio_outputs_and_ttl(self) -> None:
        root = Path("/tmp/example/CHT/LLM-only")
        expected = Path("/tmp/example/CHT/tio_outputs/llm_only/TC001.ttl")
        self.assertEqual(nl_to_tio.output_path_for_case(root, "TC001"), expected)

    def test_token_usage_path_uses_phase1_token_usage_directory(self) -> None:
        root = Path("/tmp/example/CHT/LLM-only")
        expected = Path("/tmp/example/CHT/phase1/token_usage/token_usage_llm_only.json")
        self.assertEqual(nl_to_tio.token_usage_path(root), expected)

    def test_system_prompt_requires_turtle_not_json_ld(self) -> None:
        prompt = nl_to_tio.build_system_prompt("TC001")
        self.assertIn("Turtle", prompt)
        self.assertIn("icm:PropertyExpectation", prompt)
        self.assertNotIn("intentExpectation", prompt)

    def test_system_prompt_requires_enterprise_vpn_sla_ontology_terms(self) -> None:
        prompt = nl_to_tio.build_system_prompt("TC001")

        self.assertIn("evsla:EnterpriseVpnService", prompt)
        self.assertIn("evsla:HubAndSpokeTopology", prompt)
        self.assertIn("latency -> evsla:latency", prompt)
        self.assertIn("95% -> evsla:p95", prompt)
        self.assertIn("所有分點 / 各Spoke -> evsla:hubToAllSpokes", prompt)
        self.assertNotIn("DeliveryExpectation", prompt)

    def test_chat_model_uses_gpt_5_4(self) -> None:
        self.assertEqual(nl_to_tio.CHAT_MODEL, "gpt-5.4")

    def test_generate_turtle_records_token_usage(self) -> None:
        completion = Mock()
        completion.choices = [Mock(message=Mock(content="ex:i a icm:Intent ."))]
        completion.usage = Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = completion

        with tempfile.TemporaryDirectory() as tmp:
            usage_path = Path(tmp) / "token_usage_llm_only.json"
            original_client = nl_to_tio.client
            nl_to_tio.client = mock_client
            try:
                with patch.object(nl_to_tio, "token_usage_path", return_value=usage_path):
                    result = nl_to_tio.generate_turtle_code(
                        "確保延遲低於 50ms",
                        "TC001",
                        "",
                    )
            finally:
                nl_to_tio.client = original_client

            self.assertEqual(result, "ex:i a icm:Intent .")
            rows = json.loads(usage_path.read_text(encoding="utf-8"))
            self.assertEqual(rows[0]["experiment"], "llm_only")
            self.assertEqual(rows[0]["stage"], "turtle_generation")
            self.assertEqual(rows[0]["total_tokens"], 15)


if __name__ == "__main__":
    unittest.main()
