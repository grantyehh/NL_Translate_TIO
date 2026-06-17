import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_structure_experiments as runner


class TestRunStructureExperiments(unittest.TestCase):
    def test_workflow_runs_four_generation_and_evaluation_lines(self) -> None:
        calls = []

        def fake_run_command(cmd, cwd):
            calls.append((list(cmd), cwd))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            test_cases = root / "test_cases_40.json"
            test_cases.write_text("[]", encoding="utf-8")

            with patch.object(runner, "ROOT", root), patch.object(
                runner,
                "run_command",
                side_effect=fake_run_command,
            ), patch.object(
                runner,
                "write_accuracy_summary",
            ), patch.object(
                runner,
                "write_token_summary",
            ):
                runner.run_workflow(test_cases=test_cases, eval_only=False)

        command_text = [" ".join(str(part) for part in cmd) for cmd, _cwd in calls]
        self.assertIn("LLM-only/nl_to_tio.py", command_text[0])
        self.assertIn("--prompt-profile strong", command_text[0])
        self.assertIn("LLM-only/nl_to_tio.py", command_text[1])
        self.assertIn("--prompt-profile structure_only", command_text[1])
        self.assertIn("GraphRag/nl_to_tio.py", command_text[2])
        self.assertIn("--prompt-profile structure_only", command_text[2])
        self.assertIn("KGE/KGE-based-graphrag/nl_to_tio.py", command_text[3])
        self.assertIn("--prompt-profile structure_only", command_text[3])

        eval_commands = command_text[4:8]
        self.assertEqual(len(eval_commands), 4)
        self.assertTrue(all("evaluate_ttl.py" in cmd for cmd in eval_commands))
        self.assertIn("llm_only", eval_commands[0])
        self.assertIn("llm_only_structure", eval_commands[1])
        self.assertIn("graphrag_structure", eval_commands[2])
        self.assertIn("kge_structure", eval_commands[3])

    def test_eval_only_skips_generation_but_keeps_evaluation_and_summaries(self) -> None:
        calls = []

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            test_cases = root / "test_cases_40.json"
            test_cases.write_text("[]", encoding="utf-8")

            with patch.object(runner, "ROOT", root), patch.object(
                runner,
                "run_command",
                side_effect=lambda cmd, cwd: calls.append(list(cmd)),
            ), patch.object(
                runner,
                "write_accuracy_summary",
            ) as accuracy, patch.object(
                runner,
                "write_token_summary",
            ) as token:
                runner.run_workflow(test_cases=test_cases, eval_only=True)

        command_text = [" ".join(str(part) for part in cmd) for cmd in calls]
        self.assertEqual(len(command_text), 4)
        self.assertTrue(all("evaluate_ttl.py" in cmd for cmd in command_text))
        accuracy.assert_called_once()
        token.assert_called_once()

    def test_accuracy_summary_writes_four_line_semantic_report(self) -> None:
        rows = [
            {
                "case_id": "TC001",
                "parse_ok": True,
                "expected_coverage_ratio": 1.0,
                "triple_count": 42,
                "unknown_predicates": ["p"],
                "unknown_types": [],
                "semantic": {
                    "composite": 0.75,
                    "dimensions": {
                        "metric": 1.0,
                        "threshold": 0.5,
                        "statistic": 1.0,
                        "scope": 1.0,
                        "measurement_method": 1.0,
                        "time_window": 1.0,
                        "operator": 1.0,
                        "tenant": 1.0,
                        "topology": 1.0,
                        "contract": 1.0,
                        "precision": 1.0,
                    },
                },
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = {}
            for line in runner.LINES:
                report = root / f"{line.experiment}.json"
                report.write_text(json.dumps(rows), encoding="utf-8")
                reports[line.experiment] = report
            out = root / "summary.txt"

            runner.write_accuracy_summary(reports, out)

            text = out.read_text(encoding="utf-8")
            self.assertIn("Structure Four-Line Accuracy Summary", text)
            self.assertIn("LLM ceiling", text)
            self.assertIn("LLM baseline", text)
            self.assertIn("GraphRAG", text)
            self.assertIn("KGE", text)
            self.assertIn("0.7500", text)
            self.assertIn("metric", text)

    def test_token_summary_uses_structure_variant(self) -> None:
        calls = []

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "tokens.txt"
            with patch.object(runner, "ROOT", root), patch.object(
                runner,
                "run_command",
                side_effect=lambda cmd, cwd: calls.append((list(cmd), cwd)),
            ):
                runner.write_token_summary(out)

        cmd, cwd = calls[0]
        self.assertEqual(cwd, root)
        self.assertIn("compare_token_usage.py", str(cmd[1]))
        self.assertIn("--variant", cmd)
        self.assertIn("structure", cmd)
        self.assertIn(str(out), cmd)

    def test_kge_retrain_records_prep_in_structure_token_ledger(self) -> None:
        calls = []

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(runner, "ROOT", root), patch.object(
                runner,
                "run_command",
                side_effect=lambda cmd, cwd: calls.append((list(cmd), cwd)),
            ):
                runner.run_optional_prep(
                    rebuild_graphrag_index=False,
                    retrain_kge=True,
                )

        cmd, cwd = calls[0]
        self.assertEqual(cwd, root / "KGE" / "KGE-based-graphrag")
        self.assertIn("-m", cmd)
        self.assertIn("kge.train", cmd)
        self.assertIn("--usage-experiment", cmd)
        self.assertIn("kge_structure", cmd)


if __name__ == "__main__":
    unittest.main()
