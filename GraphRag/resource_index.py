from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

TIO = "http://tio.models.tmforum.org/tio/v3.6.0/"
PREFIX_MAP = [
    ("evsla", TIO + "EnterpriseVpnSlaOntology/"),
    ("icm", TIO + "IntentCommonModel/"),
    ("imo", TIO + "IntentManagementOntology/"),
    ("met", TIO + "MetricsAndObservations/"),
    ("quan", TIO + "QuantityOntology/"),
    ("fun", TIO + "FunctionOntology/"),
    ("log", TIO + "LogicalOperators/"),
    ("rdf", str(RDF)),
    ("rdfs", str(RDFS)),
    ("skos", str(SKOS)),
    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
]

MET_METRIC = URIRef(TIO + "MetricsAndObservations/metric")
CLASS_ROLE = {
    URIRef(TIO + "EnterpriseVpnSlaOntology/Statistic"): "Statistic",
    URIRef(TIO + "EnterpriseVpnSlaOntology/Scope"): "Scope",
    URIRef(TIO + "EnterpriseVpnSlaOntology/MeasurementMethod"): "MeasurementMethod",
    URIRef(TIO + "EnterpriseVpnSlaOntology/TimeWindow"): "TimeWindow",
}
OPERATOR_URIS = {
    URIRef(TIO + "QuantityOntology/" + name)
    for name in ("smaller", "atLeast", "atMost", "greater", "inRange")
}


@dataclass(frozen=True)
class OntologyResource:
    uri: str
    curie: str
    labels: tuple[str, ...]
    alt_labels: tuple[str, ...]
    comment: str
    role: str  # "class" | "property" | "instance"
    rdf_types: tuple[str, ...]
    role_class: str | None


def to_curie(uri: str) -> str:
    for prefix, ns in PREFIX_MAP:
        if uri.startswith(ns):
            return f"{prefix}:{uri[len(ns):]}"
    return uri


def _role(types: list[URIRef]) -> str:
    if RDF.Property in types or any(str(t).endswith("Property") for t in types):
        return "property"
    if RDFS.Class in types:
        return "class"
    return "instance"


def _derive_role_class(subj: URIRef, types: list[URIRef], graph: Graph) -> str | None:
    if subj in OPERATOR_URIS:
        return "ComparisonOperator"
    for t in types:
        if t in CLASS_ROLE:
            return CLASS_ROLE[t]
    if (subj, RDFS.subPropertyOf, MET_METRIC) in graph:
        return "Metric"
    return None


def build_resource_index(graph: Graph) -> list[OntologyResource]:
    subjects = {s for s in graph.subjects() if isinstance(s, URIRef) and str(s).startswith(TIO)}
    out: list[OntologyResource] = []
    for s in subjects:
        labels = tuple(str(o) for o in graph.objects(s, RDFS.label))
        alt = tuple(str(o) for o in graph.objects(s, SKOS.altLabel))
        comments = [str(o) for o in graph.objects(s, RDFS.comment)]
        types = list(graph.objects(s, RDF.type))
        out.append(
            OntologyResource(
                uri=str(s),
                curie=to_curie(str(s)),
                labels=labels,
                alt_labels=alt,
                comment=comments[0] if comments else "",
                role=_role(types),
                rdf_types=tuple(to_curie(str(t)) for t in types),
                role_class=_derive_role_class(s, types, graph),
            )
        )
    return sorted(out, key=lambda r: r.curie)
