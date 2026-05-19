import unittest
from pathlib import Path

from rdflib import URIRef

from ontology_graph import load_ontology, build_label_index


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


class TestLabelIndex(unittest.TestCase):
    def setUp(self):
        self.idx = build_label_index(load_ontology(TTL_DIR))

    def test_label_index_maps_twamp_to_evsla_uri(self):
        self.assertIn("twamp", self.idx)
        self.assertEqual(
            str(self.idx["twamp"]),
            "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/twamp",
        )

    def test_label_index_picks_up_skos_alt_label_only_term(self):
        from rdflib import Graph, Literal, URIRef
        from rdflib.namespace import SKOS

        g = Graph()
        uri = URIRef("http://example.org/x")
        g.add((uri, SKOS.altLabel, Literal("Alt Only", lang="en")))

        idx = build_label_index(g)

        self.assertEqual(idx.get("alt only"), uri)

    def test_label_index_handles_multi_word_labels(self):
        self.assertIn("p95 statistic", self.idx)


if __name__ == "__main__":
    unittest.main()
