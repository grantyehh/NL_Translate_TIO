import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("GRAPHRAG_API_KEY", "test-key")

ROOT = Path(__file__).resolve().parents[1]
KAG_ROOT = ROOT / "KAG"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(KAG_ROOT))


def load_module():
    path = KAG_ROOT / "nl_to_tio.py"
    spec = importlib.util.spec_from_file_location("kag_nl_to_tio", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class TestKagNlToTio(unittest.TestCase):
    def test_generate_jsonld_code_delegates_to_kag_solver(self):
        nl_to_tio = load_module()

        with patch.object(nl_to_tio, "query_kag", return_value='{"@type": "Intent"}') as query_kag:
            result = nl_to_tio.generate_jsonld_code(
                "確保星河銀行總部至所有分點之延遲低於50ms。",
                "TC001",
                "--- Example 1 ---",
                verbose=True,
            )

        self.assertEqual(result, '{"@type": "Intent"}')
        query_kag.assert_called_once_with(
            "確保星河銀行總部至所有分點之延遲低於50ms。",
            tc_id="TC001",
            few_shot_block="--- Example 1 ---",
            verbose=True,
        )


if __name__ == "__main__":
    unittest.main()
