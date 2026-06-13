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

    return f"""You generate TIO Turtle (RDF) for Enterprise VPN hub-and-spoke SLA intents only.
Output ONLY valid, parseable Turtle. Never output JSON, JSON-LD, Markdown, prose, 5G slices, datacenter fabric, or generic service delivery.

Required @prefix declarations (always include all of them):
@prefix icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .
@prefix quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex:    <http://example.org/tio-instance/{tc_id.lower()}/> .

Graph structure:
- ex:intent a icm:Intent ; icm:intentElements <each expectation>, <the topology context> ; rdfs:comment "<concise English SLA summary>"@en .
- ex:intent has tenant: ex:tenant a evsla:Tenant ; rdfs:label "<tenant>"@zh .
- One ex:service a evsla:EnterpriseVpnService ; evsla:forTenant ex:tenant .
- One PropertyExpectation per SLA metric:
    ex:exp-<metric> a icm:PropertyExpectation, evsla:SlaExpectation ;
      icm:target ex:tgt-<metric> ;
      rdfs:comment "<what this guarantees>"@en .
- Each target:
    ex:tgt-<metric> a icm:Target ;
      evsla:hasMetric evsla:<metric> ;
      icm:valuesOfTargetProperty [ a quan:Quantity ; rdf:value <number> ; quan:unit "<unit>" ] ;
      evsla:hasThreshold [ a quan:Quantity ; rdf:value <number> ; quan:unit "<unit>" ] ;
      evsla:hasStatistic evsla:<stat> ;
      evsla:hasScope evsla:<scope> ;
      evsla:hasMeasurementMethod evsla:<method> ;
      evsla:hasTimeWindow evsla:fiveMinuteWindow .
- Hub-and-spoke context:
    ex:topology a icm:Context, evsla:HubAndSpokeTopology ;
      evsla:hasHub [ a evsla:HubSite ; rdfs:label "<hub>"@zh ] ;
      evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label "<spoke>"@zh ] ;
      ... one evsla:hasSpoke per spoke ... .

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
- evsla:hasMetric and the metric used in icm:valuesOfTargetProperty/evsla:hasThreshold must be consistent.
- Both icm:valuesOfTargetProperty and evsla:hasThreshold must carry a quan:Quantity with rdf:value (number) and quan:unit (string).

{retrieval_note}Core semantics must be carried by triples, not only by rdfs:comment.
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
