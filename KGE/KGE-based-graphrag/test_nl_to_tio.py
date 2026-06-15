import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import numpy as np


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

    def test_format_few_shot_block_uses_turtle_examples(self) -> None:
        examples = [{"pattern": "p", "nl_intent": "x",
                     "turtle": "ex:i a icm:Intent ."}]
        block = nl_to_tio.format_few_shot_block(examples)
        self.assertIn("Turtle:", block)
        self.assertIn("a icm:Intent", block)
        self.assertNotIn("JSON-LD:", block)

    def test_output_path_uses_tio_outputs_and_ttl(self) -> None:
        root = Path("/tmp/example/CHT/KGE/KGE-based-graphrag")
        expected = Path("/tmp/example/CHT/tio_outputs/kge/TC001.ttl")
        self.assertEqual(nl_to_tio.output_path_for_case(root, "TC001"), expected)

    def test_token_usage_path_uses_phase1_token_usage_directory(self) -> None:
        root = Path("/tmp/example/CHT/KGE/KGE-based-graphrag")
        expected = Path("/tmp/example/CHT/phase1/token_usage/token_usage_kge.json")
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

    def test_generate_turtle_records_token_usage(self) -> None:
        completion = Mock()
        completion.choices = [Mock(message=Mock(content="ex:i a icm:Intent ."))]
        completion.usage = Mock(prompt_tokens=30, completion_tokens=10, total_tokens=40)

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = completion

        with TemporaryDirectory() as tmp:
            usage_path = Path(tmp) / "token_usage_kge.json"
            with patch.object(nl_to_tio, "client", mock_client), patch.object(
                nl_to_tio,
                "token_usage_path",
                return_value=usage_path,
            ):
                create = mock_client.chat.completions.create
                result = nl_to_tio.generate_turtle_code(
                    "確保延遲低於 50ms",
                    "TC001",
                    "",
                    kge_context=(
                        "Grounded URIs:\n"
                        "- evsla:SlaExpectation\n\n"
                        "Predicted likely triples:\n"
                        "- evsla:SlaExpectation evsla:hasMetric evsla:latency"
                    ),
                )

            self.assertEqual(result, "ex:i a icm:Intent .")
            user_prompt = create.call_args.kwargs["messages"][1]["content"]
            self.assertIn("KGE grounded URI / predicted likely triples", user_prompt)
            self.assertNotIn("GraphRAG", user_prompt)
            self.assertIn("Grounded URIs:", user_prompt)
            self.assertIn("Predicted likely triples:", user_prompt)
            rows = json.loads(usage_path.read_text(encoding="utf-8"))
            self.assertEqual(rows[0]["experiment"], "kge")
            self.assertEqual(rows[0]["stage"], "turtle_generation")
            self.assertEqual(rows[0]["total_tokens"], 40)

    def test_main_uses_kge_context_without_querying_graphrag(self) -> None:
        root = Path(__file__).resolve().parent
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            usage_path = out_dir / "token_usage_kge.json"
            with patch.object(
                nl_to_tio,
                "default_test_cases_path",
                return_value=root / "_missing_default_cases.json",
            ), patch.object(
                nl_to_tio,
                "output_path_for_case",
                side_effect=lambda _root, tc_id: out_dir / f"{tc_id}.ttl",
            ), patch.object(
                nl_to_tio,
                "load_few_shot_samples",
                return_value=[],
            ), patch.object(
                nl_to_tio,
                "format_kge_context_for_prompt",
                return_value="Grounded URIs:\n- evsla:SlaExpectation",
            ), patch.object(
                nl_to_tio,
                "generate_turtle_code",
                return_value="ex:i a icm:Intent .",
            ) as generate, patch.object(
                nl_to_tio,
                "token_usage_path",
                return_value=usage_path,
            ), patch.object(
                nl_to_tio,
                "query_graphrag_local",
                side_effect=AssertionError("KGE-only must not query GraphRAG"),
                create=True,
            ), patch.object(
                sys,
                "argv",
                [
                    "nl_to_tio.py",
                    "--test-cases",
                    str(root.parent.parent / "test_cases_20.json"),
                    "--no-few-shot",
                ],
            ):
                nl_to_tio.main()

        self.assertGreater(generate.call_count, 0)
        first_call = generate.call_args_list[0]
        self.assertIn("Grounded URIs", first_call.kwargs["kge_context"])

    def test_relation_kge_artifact_paths_are_defined(self) -> None:
        from kge import paths

        self.assertEqual(paths.RELATION_IDS_JSON.name, "relation_ids.json")
        self.assertEqual(paths.RELATION_KGE_EMB_NPY.name, "relation_kge_embeddings.npy")

    def test_trans_e_link_prediction_scores_candidate_triples(self) -> None:
        from kge.retrieve import score_link_predictions

        entity_ids = [
            "http://example.test/SlaExpectation",
            "http://example.test/latency",
            "http://example.test/packetLoss",
        ]
        relation_ids = [
            "http://example.test/hasMetric",
            "http://example.test/blockedRelation",
        ]
        entity_emb = np.asarray(
            [
                [0.0, 0.0],
                [1.0, 0.0],
                [4.0, 0.0],
            ],
            dtype=np.float32,
        )
        relation_emb = np.asarray(
            [
                [1.0, 0.0],
                [0.0, 1.0],
            ],
            dtype=np.float32,
        )

        predictions = score_link_predictions(
            "http://example.test/SlaExpectation",
            entity_ids,
            relation_ids,
            entity_emb,
            relation_emb,
            relation_whitelist={"http://example.test/hasMetric"},
            candidate_tail_uris={
                "http://example.test/latency",
                "http://example.test/packetLoss",
            },
            top_k=2,
        )

        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0].relation_uri, "http://example.test/hasMetric")
        self.assertEqual(predictions[0].tail_uri, "http://example.test/latency")
        self.assertGreater(predictions[0].score, predictions[1].score)
        self.assertNotEqual(predictions[0].relation_uri, "http://example.test/blockedRelation")

    def test_grounded_kge_context_formats_predicted_likely_triples(self) -> None:
        from kge.retrieve import LinkPrediction, format_grounded_kge_context

        context = format_grounded_kge_context(
            grounded=[
                (
                    "evsla:SlaExpectation",
                    "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/SlaExpectation",
                    "text",
                    "SLA expectation class",
                )
            ],
            predictions=[
                LinkPrediction(
                    head_uri="http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/SlaExpectation",
                    relation_uri="http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/hasMetric",
                    tail_uri="http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/latency",
                    score=-0.01,
                )
            ],
        )

        self.assertIn("Grounded URIs", context)
        self.assertIn("Predicted likely triples", context)
        self.assertIn("evsla:SlaExpectation", context)
        self.assertIn("evsla:SlaExpectation evsla:hasMetric evsla:latency", context)
        self.assertIn("Use these as structural hints, not as test-case answers", context)


if __name__ == "__main__":
    unittest.main()
