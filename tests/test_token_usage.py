import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import token_usage


class TestTokenUsage(unittest.TestCase):
    def test_extract_chat_usage_accepts_openai_style_object(self) -> None:
        response = SimpleNamespace(
            usage=SimpleNamespace(
                prompt_tokens=11,
                completion_tokens=7,
                total_tokens=18,
            )
        )

        usage = token_usage.extract_usage(response)

        self.assertEqual(usage["input_tokens"], 11)
        self.assertEqual(usage["output_tokens"], 7)
        self.assertEqual(usage["total_tokens"], 18)
        self.assertEqual(usage["usage_source"], "response.usage")

    def test_extract_embedding_usage_has_zero_output_tokens(self) -> None:
        response = SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=13, total_tokens=13)
        )

        usage = token_usage.extract_usage(response)

        self.assertEqual(usage["input_tokens"], 13)
        self.assertEqual(usage["output_tokens"], 0)
        self.assertEqual(usage["total_tokens"], 13)

    def test_record_and_load_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "token_usage_llm_only.json"

            token_usage.record_usage(
                path,
                experiment="llm_only",
                ledger="online",
                case_id="TC001",
                stage="jsonld_generation",
                model="gpt-5.4",
                api="chat.completions",
                response=SimpleNamespace(
                    usage=SimpleNamespace(
                        prompt_tokens=10,
                        completion_tokens=5,
                        total_tokens=15,
                    )
                ),
            )

            rows = token_usage.load_usage_file(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["case_id"], "TC001")
            self.assertEqual(rows[0]["total_tokens"], 15)

    def test_aggregate_usage_separates_online_and_prep(self) -> None:
        rows = [
            {
                "ledger": "online",
                "case_id": "TC001",
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
            },
            {
                "ledger": "online",
                "case_id": "TC002",
                "input_tokens": 20,
                "output_tokens": 10,
                "total_tokens": 30,
            },
            {
                "ledger": "prep",
                "case_id": None,
                "input_tokens": 100,
                "output_tokens": 0,
                "total_tokens": 100,
            },
        ]

        summary = token_usage.aggregate_usage(rows, amortize_over=[2, 10])

        self.assertEqual(summary["cases_processed"], 2)
        self.assertEqual(summary["prep_total_tokens"], 100)
        self.assertEqual(summary["total_online_tokens"], 45)
        self.assertEqual(summary["avg_online_total_tokens_per_case"], 22.5)
        self.assertEqual(summary["amortized_tokens_per_case"]["2"], 72.5)
        self.assertEqual(summary["amortized_tokens_per_case"]["10"], 32.5)


if __name__ == "__main__":
    unittest.main()
