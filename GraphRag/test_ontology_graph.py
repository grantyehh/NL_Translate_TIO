import unittest
from pathlib import Path

from rdflib import URIRef

from ontology_graph import build_comment_index, build_label_index, build_type_index, load_ontology


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


class TestTypeIndex(unittest.TestCase):
    def setUp(self):
        self.idx = build_type_index(load_ontology(TTL_DIR))

    def test_type_index_lists_scope_instances(self):
        scope_cls = URIRef("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/Scope")
        instances = {str(u) for u in self.idx[scope_cls]}
        self.assertIn(
            "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/hubToAllSpokes",
            instances,
        )
        self.assertIn(
            "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/perSpoke",
            instances,
        )
        self.assertIn(
            "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/specificSpoke",
            instances,
        )

    def test_type_index_lists_statistic_instances(self):
        stat_cls = URIRef("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/Statistic")
        instances = {str(u) for u in self.idx[stat_cls]}
        self.assertIn(
            "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/p95",
            instances,
        )


class TestCommentIndex(unittest.TestCase):
    def setUp(self):
        self.idx = build_comment_index(load_ontology(TTL_DIR))

    def test_comment_index_has_evsla_latency(self):
        uri = URIRef("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/latency")
        self.assertIn(uri, self.idx)
        self.assertIn("latency", self.idx[uri].lower())

    def test_comment_index_has_evsla_hubtoallspokes(self):
        uri = URIRef("http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/hubToAllSpokes")
        self.assertIn(uri, self.idx)
        self.assertIn("spoke", self.idx[uri].lower())


if __name__ == "__main__":
    unittest.main()
