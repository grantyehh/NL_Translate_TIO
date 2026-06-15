from __future__ import annotations

from rdflib import Graph, URIRef
from rdflib.namespace import RDFS

from resource_index import OntologyResource, TIO

EVSLA = TIO + "EnterpriseVpnSlaOntology/"

CONNECTIVE_PROPERTIES: set[URIRef] = {
    URIRef(EVSLA + name)
    for name in (
        "hasMetric", "hasThreshold", "hasStatistic", "hasScope",
        "hasMeasurementMethod", "hasTimeWindow", "hasHub", "hasSpoke",
        "forTenant",
    )
}

RANGE_ROLE = {
    "evsla:Statistic": "Statistic",
    "evsla:Scope": "Scope",
    "evsla:MeasurementMethod": "MeasurementMethod",
    "evsla:TimeWindow": "TimeWindow",
    "evsla:HubSite": "HubSite",
    "evsla:SpokeSite": "SpokeSite",
    "evsla:Tenant": "Tenant",
}

METRIC_PROPERTIES = {URIRef(EVSLA + "hasMetric")}
OPERATOR_TRIGGER_PROPERTIES = {URIRef(EVSLA + "hasThreshold")}


def _to_curie(node: URIRef) -> str:
    s = str(node)
    return f"evsla:{s[len(EVSLA):]}" if s.startswith(EVSLA) else s


def traverse_connective(
    graph: Graph, grounded: list[URIRef]
) -> tuple[list[tuple[URIRef, URIRef, URIRef]], set[str]]:
    relations: list[tuple[URIRef, URIRef, URIRef]] = []
    reached: set[str] = set()

    for prop in CONNECTIVE_PROPERTIES:
        domains = list(graph.objects(prop, RDFS.domain))
        ranges = list(graph.objects(prop, RDFS.range))
        for dom in domains:
            for rng in ranges:
                relations.append((dom, prop, rng))
        for rng in ranges:
            rng_curie = _to_curie(rng) if isinstance(rng, URIRef) else str(rng)
            if prop in METRIC_PROPERTIES:
                reached.add("Metric")
            elif rng_curie in RANGE_ROLE:
                reached.add(RANGE_ROLE[rng_curie])
        if prop in OPERATOR_TRIGGER_PROPERTIES:
            reached.add("ComparisonOperator")

    relations.sort(key=lambda t: (str(t[0]), str(t[1]), str(t[2])))
    return relations, reached


def closed_vocab_for_reached_roles(
    reached: set[str], resources: list[OntologyResource]
) -> dict[str, list[str]]:
    vocab: dict[str, list[str]] = {}
    for r in resources:
        if r.role_class and r.role_class in reached:
            vocab.setdefault(r.role_class, []).append(r.curie)
    for role in vocab:
        vocab[role] = sorted(vocab[role])
    return vocab
