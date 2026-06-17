import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_index  # noqa: E402
from resource_index import OntologyResource  # noqa: E402


class TestBuildIndexTokenUsage(unittest.TestCase):
    def test_embedding_index_build_records_prep_usage(self) -> None:
        fake_resource = OntologyResource(
            uri="http://example.org/latency",
            curie="evsla:latency",
            labels=("latency",),
            alt_labels=(),
            comment="Latency metric",
            role="instance",
            rdf_types=("evsla:Metric",),
            role_class="Metric",
        )
        response = Mock()
        response.data = [SimpleNamespace(embedding=[0.1, 0.2])]
        response.usage = Mock(prompt_tokens=7, completion_tokens=0, total_tokens=7)
        mock_client = Mock()
        mock_client.embeddings.create.return_value = response

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "index"
            usage_path = Path(tmp) / "token_usage_graphrag_structure.json"
            with patch.object(build_index, "load_ontology", return_value=object()), patch.object(
                build_index,
                "build_resource_index",
                return_value=[fake_resource],
            ), patch.object(
                build_index,
                "create_embedding_client",
                return_value=mock_client,
            ), patch.object(
                build_index,
                "token_usage_path",
                return_value=usage_path,
            ):
                rc = build_index.main(["--output-dir", str(out_dir)])

            self.assertEqual(rc, 0)
            rows = json.loads(usage_path.read_text(encoding="utf-8"))
            self.assertEqual(rows[0]["experiment"], "graphrag_structure")
            self.assertEqual(rows[0]["ledger"], "prep")
            self.assertEqual(rows[0]["case_id"], None)
            self.assertEqual(rows[0]["stage"], "resource_index_embeddings")
            self.assertEqual(rows[0]["total_tokens"], 7)


if __name__ == "__main__":
    unittest.main()
