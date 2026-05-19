import unittest
from pathlib import Path

from rdflib import URIRef

from ontology_graph import load_ontology


REPO_ROOT = Path(__file__).resolve().parent.parent
TTL_DIR = REPO_ROOT / "TM Forum Intent Ontology"


class TestLoadOntology(unittest.TestCase):
    def test_load_ontology_returns_non_empty_graph(self):
        g = load_ontology(TTL_DIR)
        self.assertGreater(len(g), 0)

    def test_load_ontology_includes_evsla_terms(self):
        g = load_ontology(TTL_DIR)
        evsla_twamp = URIRef("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/twamp")
        self.assertTrue(
            any(s == evsla_twamp for s, _, _ in g),
            "evsla:twamp should be a subject in the merged graph",
        )


if __name__ == "__main__":
    unittest.main()
