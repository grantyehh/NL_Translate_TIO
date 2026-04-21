import importlib.util
import os
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


if __name__ == "__main__":
    unittest.main()
