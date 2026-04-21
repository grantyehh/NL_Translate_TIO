import os
import sys
import unittest
from pathlib import Path


os.environ.setdefault("OPENAI_API_KEY", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import nl_to_tio  # noqa: E402


class TestGraphRagPaths(unittest.TestCase):
    def test_default_test_cases_path_points_to_repo_root_shared_file(self) -> None:
        root = Path("/tmp/example/CHT/GraphRag")
        expected = Path("/tmp/example/CHT/test_cases_20.json").resolve()
        self.assertEqual(nl_to_tio.default_test_cases_path(root), expected)

    def test_default_few_shot_path_points_to_repo_root_shared_file(self) -> None:
        root = Path("/tmp/example/CHT/GraphRag")
        expected = Path("/tmp/example/CHT/few_shot_samples.json").resolve()
        self.assertEqual(nl_to_tio.default_few_shot_path(root), expected)


if __name__ == "__main__":
    unittest.main()
