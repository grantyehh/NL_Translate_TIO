import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
