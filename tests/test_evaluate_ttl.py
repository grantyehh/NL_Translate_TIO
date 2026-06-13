import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_eval():
    path = ROOT / "evaluate_ttl.py"
    spec = importlib.util.spec_from_file_location("evaluate_ttl", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestEvaluateTtl(unittest.TestCase):
    def test_experiments_map_has_four_keys_and_ttl_dirs(self) -> None:
        ev = load_eval()
        self.assertEqual(set(ev.EXPERIMENTS.keys()), {"llm_only", "graphrag", "kge", "kag"})
        for key, cfg in ev.EXPERIMENTS.items():
            self.assertTrue(str(cfg["outputs_dir"]).endswith(f"tio_outputs/{key}"))

    def test_evaluate_file_reports_expected_coverage(self) -> None:
        ev = load_eval()
        ttl = (
            "@prefix icm: <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .\n"
            "@prefix ex: <http://example.org/x/> .\n"
            "ex:i a icm:Intent ; icm:intentElements ex:e .\n"
            "ex:e a icm:PropertyExpectation ; icm:target ex:t .\n"
            "ex:t a icm:Target ; icm:valuesOfTargetProperty ex:v .\n"
        )
        tmp = ROOT / "tio_outputs" / "llm_only"
        tmp.mkdir(parents=True, exist_ok=True)
        f = tmp / "TCTEST.ttl"
        f.write_text(ttl, encoding="utf-8")
        try:
            row = ev.evaluate_file(f, ["icm:Intent", "icm:PropertyExpectation", "icm:Target", "icm:valuesOfTargetProperty"], "TCTEST")
            self.assertTrue(row["parse_ok"])
            self.assertEqual(row["expected_coverage_ratio"], 1.0)
        finally:
            f.unlink()


if __name__ == "__main__":
    unittest.main()
