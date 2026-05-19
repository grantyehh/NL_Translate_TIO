import json
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import evaluate_jsonld


VALID_INTENT = {
    "@context": "https://tmforum.org/schemas/intent-ontology/v1.jsonld",
    "@type": "Intent",
    "id": "intent-tc002",
    "name": "Gaming User Performance Intent",
    "description": "Guarantee gaming users throughput and latency.",
    "intentOwner": {"id": "ops-manager-01", "name": "Network Operations Center"},
    "intentExpectation": [
        {
            "id": "exp-throughput-01",
            "name": "Throughput Expectation",
            "description": "Downlink throughput must exceed 100 Mbps.",
            "@type": "PropertyExpectation",
            "expectationObject": {"id": "service-gaming-users", "name": "Gaming Users", "@type": "Service"},
            "expectationTarget": [
                {
                    "name": "Downlink Throughput",
                    "targetProperty": "throughput",
                    "matchCondition": "GREATER_THAN",
                    "targetValue": {"value": 100, "unit": "Mbps"},
                }
            ],
        }
    ],
    "intentContext": [],
    "intentReport": {"reportingInterval": "PT5M", "handlerResponse": "Continuous"},
}

VALID_EVSLA_INTENT = {
    "@context": "https://tmforum.org/schemas/intent-ontology/v1.jsonld",
    "@type": "Intent",
    "id": "intent-tc001",
    "name": "Enterprise VPN Hub-Spoke SLA Intent",
    "description": "Ensure 星河銀行 hub-to-spoke latency stays below 50 ms for 95 percent of the time.",
    "ontologyType": "evsla:EnterpriseVpnSlaIntent",
    "intentOwner": {"id": "ops-manager-01", "name": "Network Operations Center"},
    "tenant": {"id": "tenant-星河銀行", "name": "星河銀行", "@type": "evsla:Tenant"},
    "intentExpectation": [
        {
            "id": "exp-latency-01",
            "name": "Hub-to-Spoke Latency SLA Expectation",
            "description": "Latency must be below 50 ms at p95.",
            "@type": "PropertyExpectation",
            "ontologyType": "evsla:SlaExpectation",
            "expectationObject": {
                "id": "svc:星河銀行-enterprise-vpn",
                "name": "星河銀行 Enterprise VPN Service",
                "@type": "Service",
                "ontologyType": "evsla:EnterpriseVpnService",
            },
            "expectationTarget": [
                {
                    "name": "Hub-to-Spoke Latency",
                    "targetProperty": "evsla:latency",
                    "matchCondition": "LESS_THAN",
                    "targetValue": {"value": 50, "unit": "ms", "@type": "quan:Quantity"},
                    "evsla:hasMetric": "evsla:latency",
                    "evsla:hasThreshold": {"value": 50, "unit": "ms", "@type": "quan:Quantity"},
                    "evsla:hasStatistic": "evsla:p95",
                    "evsla:hasScope": "evsla:hubToAllSpokes",
                    "evsla:hasMeasurementMethod": "evsla:twamp",
                    "evsla:hasTimeWindow": "evsla:fiveMinuteWindow",
                }
            ],
        }
    ],
    "intentContext": [
        {
            "id": "topology-tc001",
            "@type": "Context",
            "name": "Hub-and-Spoke Topology",
            "ontologyType": "evsla:HubAndSpokeTopology",
            "evsla:hasHub": {"@type": "evsla:HubSite", "name": "台北總部"},
            "evsla:hasSpoke": [{"@type": "evsla:SpokeSite", "name": "新竹分行"}],
        }
    ],
    "intentReport": {"reportingInterval": "PT5M", "handlerResponse": "Continuous"},
}


class TestEvaluateJsonLd(unittest.TestCase):
    def test_evaluate_payload_reports_contract_and_expected_coverage(self) -> None:
        report = evaluate_jsonld.evaluate_payload(
            VALID_INTENT,
            expected_elements=["icm:PropertyExpectation", "icm:Target", "icm:valuesOfTargetProperty"],
            case_id="TC002",
            file_path=Path("TC002.jsonld"),
            markdown_fence_stripped=False,
            parse_error=None,
        )

        self.assertTrue(report["parse_ok"])
        self.assertEqual(report["contract_errors"], [])
        self.assertEqual(report["expected_coverage_ratio"], 1.0)
        self.assertTrue(report["intent_uri_contains_case_id"])
        self.assertGreater(report["triple_count"], 0)

    def test_property_expectation_without_structured_target_fails_contract(self) -> None:
        payload = json.loads(json.dumps(VALID_INTENT))
        del payload["intentExpectation"][0]["expectationTarget"][0]["targetValue"]

        report = evaluate_jsonld.evaluate_payload(
            payload,
            expected_elements=["icm:PropertyExpectation"],
            case_id="TC002",
            file_path=Path("TC002.jsonld"),
            markdown_fence_stripped=False,
            parse_error=None,
        )

        self.assertFalse(report["parse_ok"])
        self.assertIn("JSONLD_TARGET_VALUE", {err["code"] for err in report["contract_errors"]})

    def test_evaluate_payload_scores_ontology_terms_and_performance_metrics(self) -> None:
        report = evaluate_jsonld.evaluate_payload(
            VALID_EVSLA_INTENT,
            expected_elements=["icm:PropertyExpectation", "icm:Target"],
            case_id="TC001",
            file_path=Path("TC001.jsonld"),
            markdown_fence_stripped=False,
            parse_error=None,
            ontology_terms=[
                "evsla:EnterpriseVpnSlaIntent",
                "evsla:EnterpriseVpnService",
                "evsla:HubAndSpokeTopology",
                "evsla:latency",
                "evsla:p95",
                "evsla:twamp",
            ],
            performance_metrics=[
                {
                    "metric": "latency",
                    "operator": "LESS_THAN",
                    "threshold": {"value": 50, "unit": "ms"},
                    "ontology_term": "evsla:latency",
                    "statistic": "evsla:p95",
                    "scope": "evsla:hubToAllSpokes",
                    "measurement_method": "evsla:twamp",
                    "time_window": "evsla:fiveMinuteWindow",
                }
            ],
        )

        self.assertEqual(report["ontology_term_coverage_ratio"], 1.0)
        self.assertEqual(report["performance_metric_coverage_ratio"], 1.0)

    def test_evaluate_payload_scores_json_node_budget_range(self) -> None:
        actual_nodes = evaluate_jsonld.count_json_nodes(VALID_EVSLA_INTENT)

        report = evaluate_jsonld.evaluate_payload(
            VALID_EVSLA_INTENT,
            expected_elements=["icm:PropertyExpectation"],
            case_id="TC001",
            file_path=Path("TC001.jsonld"),
            markdown_fence_stripped=False,
            parse_error=None,
            expected_json_nodes={
                "target": actual_nodes,
                "min": actual_nodes - 2,
                "max": actual_nodes + 2,
            },
        )

        self.assertTrue(report["json_node_budget"]["ok"])
        self.assertEqual(report["json_node_budget"]["actual"], actual_nodes)
        self.assertEqual(report["json_node_budget"]["delta"], 0)
        self.assertEqual(report["json_node_budget"]["ratio"], 1.0)

    def test_evaluate_payload_flags_json_node_budget_over_max(self) -> None:
        actual_nodes = evaluate_jsonld.count_json_nodes(VALID_EVSLA_INTENT)

        report = evaluate_jsonld.evaluate_payload(
            VALID_EVSLA_INTENT,
            expected_elements=["icm:PropertyExpectation"],
            case_id="TC001",
            file_path=Path("TC001.jsonld"),
            markdown_fence_stripped=False,
            parse_error=None,
            expected_json_nodes={
                "target": actual_nodes - 10,
                "min": actual_nodes - 20,
                "max": actual_nodes - 5,
            },
        )

        self.assertFalse(report["json_node_budget"]["ok"])
        self.assertEqual(report["json_node_budget"]["status"], "too_verbose")

    def test_evaluate_payload_penalizes_5g_output_missing_evsla_terms_and_threshold(self) -> None:
        old_5g_output = json.loads(json.dumps(VALID_INTENT))
        old_5g_output["id"] = "intent-tc001"
        old_5g_output["name"] = "5G Slice Service Establishment Intent"

        report = evaluate_jsonld.evaluate_payload(
            old_5g_output,
            expected_elements=["icm:PropertyExpectation", "icm:Target"],
            case_id="TC001",
            file_path=Path("TC001.jsonld"),
            markdown_fence_stripped=False,
            parse_error=None,
            ontology_terms=["evsla:EnterpriseVpnSlaIntent", "evsla:latency", "evsla:p95"],
            performance_metrics=[
                {
                    "metric": "latency",
                    "operator": "LESS_THAN",
                    "threshold": {"value": 50, "unit": "ms"},
                    "ontology_term": "evsla:latency",
                    "statistic": "evsla:p95",
                    "scope": "evsla:hubToAllSpokes",
                    "measurement_method": "evsla:twamp",
                    "time_window": "evsla:fiveMinuteWindow",
                }
            ],
        )

        self.assertEqual(report["ontology_term_coverage_ratio"], 0.0)
        self.assertEqual(report["performance_metric_coverage_ratio"], 0.0)

    def test_main_uses_convention_paths_for_selected_experiment(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            outputs = root / "jsonld_outputs" / "kge_hybrid"
            outputs.mkdir(parents=True)
            (outputs / "TC002.jsonld").write_text(json.dumps(VALID_INTENT), encoding="utf-8")
            cases = root / "test_cases_20.json"
            cases.write_text(
                json.dumps(
                    [
                        {
                            "id": "TC002",
                            "nl_intent": "保證所有電競用戶的下行速度高於 100Mbps 且延遲小於 10ms。",
                            "expected_tio_elements": [
                                "icm:PropertyExpectation",
                                "icm:Target",
                                "icm:valuesOfTargetProperty",
                            ],
                            "ontology_terms": ["evsla:latency"],
                            "performance_metrics": [],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            report_path = root / "phase1" / "phase1_kge_hybrid.json"

            with patch.object(evaluate_jsonld, "ROOT", root), redirect_stdout(io.StringIO()):
                code = evaluate_jsonld.main(["kge_hybrid"])

            self.assertEqual(code, 0)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report[0]["case_id"], "TC002")
            self.assertTrue(report[0]["parse_ok"])

    def test_main_rejects_legacy_path_arguments(self) -> None:
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                evaluate_jsonld.main(["--outputs-dir", "LLM-only/jsonld_outputs"])


if __name__ == "__main__":
    unittest.main()
