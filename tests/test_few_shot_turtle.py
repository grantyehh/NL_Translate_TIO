import json
import unittest
from pathlib import Path

from rdflib import Graph

ROOT = Path(__file__).resolve().parent.parent
FEW_SHOT = ROOT / "few_shot_samples.json"
PREFIXES = """@prefix icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .
@prefix quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
"""


class TestFewShotTurtle(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(FEW_SHOT.read_text(encoding="utf-8"))
        self.examples = self.data["examples"]

    def test_examples_use_turtle_field_not_jsonld(self) -> None:
        for ex in self.examples:
            self.assertIn("turtle", ex)
            self.assertNotIn("jsonld", ex)

    def test_each_turtle_parses_and_has_core_elements(self) -> None:
        for ex in self.examples:
            ttl = ex["turtle"]
            # few-shot 範例自帶 @prefix;若缺則補上共用前綴再解析
            body = ttl if "@prefix ex:" in ttl else PREFIXES + ttl
            g = Graph()
            g.parse(data=body, format="turtle")
            text = g.serialize(format="nt")
            for needle in ("IntentCommonModel/Intent", "IntentCommonModel/PropertyExpectation",
                           "IntentCommonModel/Target", "IntentCommonModel/Context",
                           "valuesOfTargetProperty"):
                self.assertIn(needle, text, f"{ex['pattern']} missing {needle}")


if __name__ == "__main__":
    unittest.main()
