from __future__ import annotations


def build_evsla_system_prompt(tc_id: str, retrieval_mode: str | None = None) -> str:
    retrieval_note = ""
    if retrieval_mode:
        retrieval_note = f"""
Retrieval context ({retrieval_mode}) is auxiliary:
- Use it to confirm EVSLA/TIO vocabulary, service ids, metric/statistic/scope/method semantics.
- If retrieval conflicts with this EVSLA schema, follow this schema.
- Do not copy retrieval prose into description.
"""

    return f"""You generate API-friendly TIO JSON-LD for Enterprise VPN hub-and-spoke SLA intents only.
Never output 5G, datacenter fabric, generic service delivery, generic traffic class, Turtle, Markdown, or prose.

Required JSON object:
- @context: "https://tmforum.org/schemas/intent-ontology/v1.jsonld"
- @type: "Intent"
- id: "intent-{tc_id.lower()}"
- name: "Enterprise VPN Hub-Spoke SLA Intent"
- description: concise English SLA summary
- ontologyType: "evsla:EnterpriseVpnSlaIntent"
- intentOwner: {{ "id": "ops-manager-01", "name": "Network Operations Center" }}
- tenant: {{ "id": "tenant:<tenant>", "name": "<tenant>", "@type": "evsla:Tenant" }}
- intentExpectation: one PropertyExpectation per SLA metric
- intentContext: one hub-and-spoke Context
- intentReport: {{ "reportingInterval": "PT5M", "handlerResponse": "Continuous" }}

Each expectation:
- @type: "PropertyExpectation"
- ontologyType: "evsla:SlaExpectation"
- expectationObject: {{ "id": "svc:<tenant>-enterprise-vpn", "name": "<tenant> Enterprise VPN Service", "@type": "Service", "ontologyType": "evsla:EnterpriseVpnService" }}
- expectationTarget: include name, targetProperty, matchCondition, targetValue, evsla:hasMetric, evsla:hasThreshold, evsla:hasStatistic, evsla:hasScope, evsla:hasMeasurementMethod, evsla:hasTimeWindow

Metric mappings:
- latency -> evsla:latency, LESS_THAN, evsla:twamp
- packet_loss / 封包遺失率 -> evsla:packetLoss, LESS_THAN, evsla:twamp
- guaranteed_bandwidth / 保證頻寬 -> evsla:guaranteedBandwidth, GREATER_THAN_OR_EQUAL, evsla:minimum, evsla:activeMeasurement
- 95% -> evsla:p95
- 99% -> evsla:p99
- all spokes / 所有分點 / 各Spoke -> evsla:hubToAllSpokes
- named single spoke / 指定單一 Spoke -> evsla:specificSpoke
- default time window -> evsla:fiveMinuteWindow

Target rules:
- targetProperty and evsla:hasMetric must both use the same evsla metric.
- targetValue and evsla:hasThreshold must both include {{ "value": number, "unit": string, "@type": "quan:Quantity" }}.

Hub-spoke context:
- @type: "Context"
- name: "Hub-and-Spoke Topology"
- ontologyType: "evsla:HubAndSpokeTopology"
- evsla:hasHub: {{ "@type": "evsla:HubSite", "name": "<hub>" }}
- evsla:hasSpoke: array of {{ "@type": "evsla:SpokeSite", "name": "<spoke>" }}

{retrieval_note}Core semantics must be structured JSON fields, not only description.
"""


def build_evsla_graphrag_query(nl_intent: str) -> str:
    return (
        "請在本專案的 TM Forum Intent Ontology v3.6.0 與 EnterpriseVpnSlaOntology TTL 知識中，"
        f"檢索並說明下列 Enterprise VPN Hub-Spoke SLA 意圖應如何建模：「{nl_intent}」。\n"
        "請優先回傳 EVSLA/TIO 官方 CURIE 與用途，避免泛用網路服務或行動網路切片詞彙，尤其是：\n"
        "- evsla:EnterpriseVpnSlaIntent, evsla:EnterpriseVpnService, evsla:Tenant\n"
        "- evsla:HubAndSpokeTopology, evsla:HubSite, evsla:SpokeSite, evsla:SlaExpectation\n"
        "- evsla:latency, evsla:packetLoss, evsla:guaranteedBandwidth\n"
        "- evsla:p95, evsla:p99, evsla:minimum\n"
        "- evsla:hubToAllSpokes, evsla:specificSpoke\n"
        "- evsla:twamp, evsla:activeMeasurement, evsla:fiveMinuteWindow\n"
        "請簡短說明 tenant、hub、spokes、metric、operator、threshold、statistic、scope、measurement method、time window 應如何放入 JSON-LD。"
    )
