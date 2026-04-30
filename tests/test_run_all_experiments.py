import subprocess
import sys
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
