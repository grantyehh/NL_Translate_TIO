import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestCompareReportsCli(unittest.TestCase):
    def test_help_documents_three_way_comparison_only(self) -> None:
        result = subprocess.run(
            [sys.executable, "compare_reports.py", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn("three phase1 reports", result.stdout)
        self.assertNotIn("--base", result.stdout)
        self.assertNotIn("--target", result.stdout)
        self.assertNotIn("--base-name", result.stdout)
        self.assertNotIn("--target-name", result.stdout)


if __name__ == "__main__":
    unittest.main()
