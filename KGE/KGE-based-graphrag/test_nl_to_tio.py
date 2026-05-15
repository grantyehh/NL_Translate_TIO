import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


os.environ.setdefault("OPENAI_API_KEY", "test-key")


def load_module():
    base = Path(__file__).resolve().parent
    path = base / "nl_to_tio.py"
    sys.path.insert(0, str(base))
    spec = importlib.util.spec_from_file_location("kge_nl_to_tio", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


nl_to_tio = load_module()


class TestKgePaths(unittest.TestCase):
    def test_default_test_cases_path_points_to_repo_root_shared_file(self) -> None:
        root = Path("/tmp/example/CHT/KGE/KGE-based-graphrag")
        expected = Path("/tmp/example/CHT/test_cases_20.json").resolve()
        self.assertEqual(nl_to_tio.default_test_cases_path(root), expected)

    def test_default_few_shot_path_points_to_repo_root_shared_file(self) -> None:
        root = Path("/tmp/example/CHT/KGE/KGE-based-graphrag")
        expected = Path("/tmp/example/CHT/few_shot_samples.json").resolve()
        self.assertEqual(nl_to_tio.default_few_shot_path(root), expected)

    def test_shared_graphrag_root_points_to_graph_rag_index(self) -> None:
        root = Path("/tmp/example/CHT/KGE/KGE-based-graphrag")
        expected = Path("/tmp/example/CHT/GraphRag").resolve()
        self.assertEqual(nl_to_tio.shared_graphrag_root(root), expected)

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
        root = Path("/tmp/example/CHT/KGE/KGE-based-graphrag")
        expected = Path("/tmp/example/CHT/jsonld_outputs/kge_hybrid/TC001.jsonld")
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

    def test_kge_retrieve_import_does_not_depend_on_root_evaluator(self) -> None:
        base = Path(__file__).resolve().parent
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import kge.retrieve as r; "
                    "print(r._uri_to_curie('http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/Intent'))"
                ),
            ],
            cwd=base,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertEqual(result.stdout.strip(), "icm:Intent")

    def test_query_graphrag_local_uses_shared_graph_rag_root(self) -> None:
        shared_root = Path("/tmp/example/CHT/GraphRag")
        completed = Mock(stdout="context")

        with patch.object(nl_to_tio.subprocess, "run", return_value=completed) as run:
            result = nl_to_tio.query_graphrag_local("query text", shared_root)

        self.assertEqual(result, "context")
        args = run.call_args.args[0]
        self.assertEqual(args[:4], ["graphrag", "query", "--root", str(shared_root)])
        self.assertIn("--method", args)
        self.assertIn("local", args)


if __name__ == "__main__":
    unittest.main()
