import subprocess
import sys
import unittest
from pathlib import Path

import run_all_experiments


ROOT = Path(__file__).resolve().parents[1]


class TestRunAllExperimentsCli(unittest.TestCase):
    def test_help_only_documents_phase1_workflow(self) -> None:
        result = subprocess.run(
            [sys.executable, "run_all_experiments.py", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertNotIn("--phase", result.stdout)
        self.assertNotIn("phase2", result.stdout.lower())
        self.assertNotIn("{phase1,phase2,all}", result.stdout)

    def test_phase1_subdirectories_are_defined(self) -> None:
        self.assertEqual(
            run_all_experiments.OUTPUT_QUALITY_DIR,
            ROOT / "phase1" / "output_quality",
        )
        self.assertEqual(
            run_all_experiments.TOKEN_USAGE_DIR,
            ROOT / "phase1" / "token_usage",
        )

    def test_phase1_evaluator_points_to_evaluate_ttl(self) -> None:
        self.assertEqual(
            run_all_experiments.PHASE1_EVALUATOR,
            ROOT / "evaluate_ttl.py",
        )

    def test_experiments_has_four_methods(self) -> None:
        self.assertEqual(
            set(run_all_experiments.EXPERIMENTS.keys()),
            {"llm_only", "graphrag", "kge", "kag"},
        )


if __name__ == "__main__":
    unittest.main()
