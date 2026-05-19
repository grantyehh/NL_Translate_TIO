import subprocess
import sys
import unittest
from pathlib import Path

import compare_reports


ROOT = Path(__file__).resolve().parents[1]


class TestCompareReportsCli(unittest.TestCase):
    def test_help_documents_four_way_comparison_only(self) -> None:
        result = subprocess.run(
            [sys.executable, "compare_reports.py", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn("LLM-only, GraphRag, KGE-hybrid, and KAG", result.stdout)
        self.assertNotIn("--base", result.stdout)
        self.assertNotIn("--target", result.stdout)
        self.assertNotIn("--base-name", result.stdout)
        self.assertNotIn("--target-name", result.stdout)

    def test_aggregate_metrics_reports_json_node_budget(self) -> None:
        metrics = compare_reports.aggregate_metrics(
            [
                {
                    "parse_ok": True,
                    "json_node_count": 60,
                    "expected_coverage_ratio": 1.0,
                    "ontology_term_coverage_ratio": 1.0,
                    "performance_metric_coverage_ratio": 1.0,
                    "intent_uri_contains_case_id": True,
                    "json_node_budget": {"ok": True, "ratio": 1.0},
                },
                {
                    "parse_ok": True,
                    "json_node_count": 90,
                    "expected_coverage_ratio": 1.0,
                    "ontology_term_coverage_ratio": 1.0,
                    "performance_metric_coverage_ratio": 1.0,
                    "intent_uri_contains_case_id": True,
                    "json_node_budget": {"ok": False, "ratio": 1.5},
                },
            ]
        )

        self.assertEqual(metrics["json_node_budget_ok_rate"], 0.5)
        self.assertEqual(metrics["avg_json_node_budget_ratio"], 1.25)


if __name__ == "__main__":
    unittest.main()
