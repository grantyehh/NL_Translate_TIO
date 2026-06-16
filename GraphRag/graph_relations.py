from __future__ import annotations

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS

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
    grounded_set = {g for g in grounded if isinstance(g, URIRef)}

    prop_info: dict[URIRef, tuple[list, list]] = {}
    for prop in CONNECTIVE_PROPERTIES:
        domains = list(graph.objects(prop, RDFS.domain))
        ranges = list(graph.objects(prop, RDFS.range))
        prop_info[prop] = (domains, ranges)

    def _directly_hit(domains, ranges) -> bool:
        for g in grounded_set:
            if g in domains or g in ranges:
                return True
            for r in ranges:
                if isinstance(r, URIRef) and (g, RDF.type, r) in graph:
                    return True
        return False

    # Hubs (property domains) that a grounded seed directly connects to.
    # Reaching a hub exposes ALL its connective role edges (spec 7.2).
    active_hubs: set = set()
    fortenant_active = False
    for prop, (domains, ranges) in prop_info.items():
        if _directly_hit(domains, ranges):
            if domains:
                active_hubs.update(d for d in domains if isinstance(d, URIRef))
            else:
                fortenant_active = True  # forTenant has no rdfs:domain

    relations: list[tuple[URIRef, URIRef, URIRef]] = []
    reached: set[str] = set()
    for prop, (domains, ranges) in prop_info.items():
        if domains:
            if not any(d in active_hubs for d in domains):
                continue
        elif not fortenant_active:
            continue
        for d in domains:
            for r in ranges:
                relations.append((d, prop, r))
        for r in ranges:
            rng_curie = _to_curie(r) if isinstance(r, URIRef) else str(r)
            if prop in METRIC_PROPERTIES:
                reached.add("Metric")
            elif rng_curie in RANGE_ROLE:
                reached.add(RANGE_ROLE[rng_curie])
        if prop in OPERATOR_TRIGGER_PROPERTIES:
            reached.add("ComparisonOperator")

    # When an SLA expectation is present (a metric is reached), the SLA-defining
    # roles are always relevant — supply their vocab regardless of traversal
    # happenstance (forTenant has no rdfs:domain; hub/spoke depend on topology
    # being grounded). This is the closed-world contract for EVSLA.
    if "Metric" in reached:
        reached.update({
            "Tenant", "MeasurementMethod", "TimeWindow",
            "HubSite", "SpokeSite", "HubAndSpokeTopology",
        })
        # Emit the forTenant relation so the prompt sees evsla:Tenant as a type.
        fortenant = URIRef(EVSLA + "forTenant")
        service = URIRef(EVSLA + "EnterpriseVpnService")
        for r in graph.objects(fortenant, RDFS.range):
            triple = (service, fortenant, r)
            if triple not in relations:
                relations.append(triple)

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
