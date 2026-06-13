import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import compare_token_usage


ROOT = Path(__file__).resolve().parents[1]


class TestCompareTokenUsage(unittest.TestCase):
    def test_help_documents_amortize_over(self) -> None:
        result = subprocess.run(
            [sys.executable, "compare_token_usage.py", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn("--amortize-over", result.stdout)
        self.assertIn("20", result.stdout)
        self.assertIn("1000", result.stdout)

    def test_emit_report_shows_online_prep_and_amortized_costs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "token_usage_llm_only.json"
            path.write_text(
                json.dumps(
                    [
                        {
                            "experiment": "llm_only",
                            "ledger": "online",
                            "case_id": "TC001",
                            "stage": "turtle_generation",
                            "input_tokens": 10,
                            "output_tokens": 5,
                            "total_tokens": 15,
                        },
                        {
                            "experiment": "llm_only",
                            "ledger": "prep",
                            "case_id": None,
                            "stage": "prep_check",
                            "input_tokens": 100,
                            "output_tokens": 0,
                            "total_tokens": 100,
                        },
                    ]
                ),
                encoding="utf-8",
            )

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                compare_token_usage.emit_report(
                    [("LLM-only", path)],
                    amortize_over=[20, 100],
                )

            report = buffer.getvalue()
            self.assertIn("Token Usage Summary", report)
            self.assertIn("LLM-only", report)
            self.assertIn("Prep total", report)
            self.assertIn("Amortized @20", report)
            self.assertIn("20.00", report)
            self.assertIn("16.00", report)

    def test_emit_report_marks_missing_telemetry_as_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.json"

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                compare_token_usage.emit_report(
                    [("KAG", missing)],
                    amortize_over=[20],
                )

            report = buffer.getvalue()
            self.assertIn("KAG", report)
            self.assertIn("MISSING", report)


if __name__ == "__main__":
    unittest.main()
