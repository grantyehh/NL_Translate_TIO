from __future__ import annotations

import re
from hashlib import sha1
from pathlib import Path
from typing import Iterable

from rdflib import BNode, Graph, Literal, RDF, RDFS, SKOS, URIRef
from rdflib.namespace import DCTERMS


IMPORTANT_PREDICATES = [
    RDF.type,
    RDFS.subClassOf,
    RDFS.subPropertyOf,
    RDFS.domain,
    RDFS.range,
    RDFS.label,
    RDFS.comment,
    SKOS.altLabel,
    SKOS.changeNote,
    DCTERMS.description,
    DCTERMS.subject,
]


PREFIXES = {
    "icm": "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/",
    "imo": "http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/",
    "fun": "http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/",
    "log": "http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/",
    "math": "http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions/",
    "set": "http://tio.models.tmforum.org/tio/v3.6.0/SetOperators/",
    "met": "http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/",
    "quan": "http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/",
    "ig": "http://tio.models.tmforum.org/tio/v3.6.0/IntentGuaranteeOntology/",
    "insp": "http://tio.models.tmforum.org/tio/v3.6.0/IntentSpecification/",
    "pbi": "http://tio.models.tmforum.org/tio/v3.6.0/ProposalBestIntent/",
    "pre": "http://tio.models.tmforum.org/tio/v3.6.0/PreferenceOfHandlingOutcomes/",
    "pro": "http://tio.models.tmforum.org/tio/v3.6.0/IntentProbing/",
    "ut": "http://tio.models.tmforum.org/tio/v3.6.0/Utility/",
    "evsla": "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dct": "http://purl.org/dc/terms/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}


def prefix_preamble() -> str:
    return "\n".join(f"@prefix {prefix}: <{namespace}> ." for prefix, namespace in PREFIXES.items()) + "\n"


def bind_prefixes(graph: Graph) -> None:
    for prefix, namespace in PREFIXES.items():
        graph.bind(prefix, namespace)


def curie(graph: Graph, value) -> str:
    if isinstance(value, Literal):
        lang = f"@{value.language}" if value.language else ""
        datatype = f"^^{curie(graph, value.datatype)}" if value.datatype else ""
        return f"{value}{lang}{datatype}"
    if isinstance(value, BNode):
        return "_:blank"
    if not isinstance(value, URIRef):
        return str(value)
    try:
        return graph.namespace_manager.normalizeUri(value)
    except Exception:
        return str(value)


def filename_for(module_name: str, term: str, uri: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", term).strip("_")
    digest = sha1(uri.encode("utf-8")).hexdigest()[:8]
    return f"{module_name}__{safe}__{digest}.txt"


def values(graph: Graph, subject: URIRef, predicate: URIRef) -> list[str]:
    return [curie(graph, obj) for obj in graph.objects(subject, predicate)]


def literal_values(graph: Graph, subject: URIRef, predicate: URIRef) -> list[str]:
    return [str(obj) for obj in graph.objects(subject, predicate) if isinstance(obj, Literal)]


def is_documentable_term(graph: Graph, subject) -> bool:
    if not isinstance(subject, URIRef):
        return False
    uri = str(subject)
    if not uri.startswith("http://tio.models.tmforum.org/tio/v3.6.0/"):
        return False
    if (subject, RDF.type, RDFS.Class) in graph:
        return True
    if (subject, RDF.type, RDF.Property) in graph:
        return True
    if list(graph.objects(subject, RDFS.label)) or list(graph.objects(subject, RDFS.comment)):
        return True
    return any(graph.objects(subject, predicate) for predicate in IMPORTANT_PREDICATES)


def outgoing_facts(graph: Graph, subject: URIRef) -> list[str]:
    rows: list[str] = []
    for predicate in IMPORTANT_PREDICATES:
        for obj in graph.objects(subject, predicate):
            rows.append(f"- {curie(graph, predicate)}: {curie(graph, obj)}")
    return rows


def incoming_facts(graph: Graph, subject: URIRef) -> list[str]:
    rows: list[str] = []
    for predicate in (RDFS.domain, RDFS.range, RDFS.subClassOf, RDFS.subPropertyOf):
        for src in graph.subjects(predicate, subject):
            if isinstance(src, URIRef):
                rows.append(f"- {curie(graph, src)} {curie(graph, predicate)} {curie(graph, subject)}")
    return rows


def related_properties(graph: Graph, subject: URIRef) -> list[str]:
    rows: list[str] = []
    for prop in graph.subjects(RDFS.domain, subject):
        if isinstance(prop, URIRef):
            rows.append(f"- domain property: {curie(graph, prop)}")
    for prop in graph.subjects(RDFS.range, subject):
        if isinstance(prop, URIRef):
            rows.append(f"- range property: {curie(graph, prop)}")
    return sorted(set(rows))


def term_kind(graph: Graph, subject: URIRef) -> str:
    if (subject, RDF.type, RDFS.Class) in graph:
        return "Class"
    if (subject, RDF.type, RDF.Property) in graph:
        return "Property"
    types = values(graph, subject, RDF.type)
    return f"Individual ({', '.join(types)})" if types else "Resource"


def write_term_document(graph: Graph, module_name: str, subject: URIRef, output_dir: Path) -> None:
    term = curie(graph, subject)
    label = literal_values(graph, subject, RDFS.label)
    comments = literal_values(graph, subject, RDFS.comment)
    descriptions = literal_values(graph, subject, DCTERMS.description)
    alt_labels = literal_values(graph, subject, SKOS.altLabel)

    lines = [
        f"Term: {term}",
        f"URI: {subject}",
        f"Module: {module_name}",
        f"Kind: {term_kind(graph, subject)}",
    ]

    if label:
        lines.append(f"Label: {'; '.join(label)}")
    if alt_labels:
        lines.append(f"Alternative labels: {'; '.join(alt_labels)}")
    if comments or descriptions:
        lines.append("")
        lines.append("Description:")
        for text in comments + descriptions:
            lines.append(f"- {text}")

    fact_rows = outgoing_facts(graph, subject)
    if fact_rows:
        lines.append("")
        lines.append("RDF facts:")
        lines.extend(fact_rows)

    incoming_rows = incoming_facts(graph, subject)
    if incoming_rows:
        lines.append("")
        lines.append("Incoming structural references:")
        lines.extend(sorted(set(incoming_rows)))

    prop_rows = related_properties(graph, subject)
    if prop_rows:
        lines.append("")
        lines.append("Related properties:")
        lines.extend(prop_rows)

    lines.append("")
    lines.append("Retrieval guidance:")
    lines.append(
        f"Use {term} when a natural-language intent asks for this ontology concept, and preserve the exact CURIE in generated Turtle or reasoning context when applicable."
    )

    path = output_dir / filename_for(module_name, term, str(subject))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_ttl_file(path: Path) -> Graph:
    graph = Graph()
    bind_prefixes(graph)
    content = path.read_text(encoding="utf-8")
    graph.parse(data=prefix_preamble() + content, format="turtle")
    return graph


def iter_terms(graph: Graph) -> Iterable[URIRef]:
    return sorted(
        (subject for subject in set(graph.subjects()) if is_documentable_term(graph, subject)),
        key=lambda item: curie(graph, item),
    )


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    ontology_dir = project_root / "TM Forum Intent Ontology"
    output_dir = project_root / "graphrag_term_input"

    output_dir.mkdir(parents=True, exist_ok=True)
    for old_file in output_dir.glob("*.txt"):
        old_file.unlink()

    total = 0
    for ttl_path in sorted(ontology_dir.glob("*.ttl")):
        print(f"Processing {ttl_path.name}...")
        graph = parse_ttl_file(ttl_path)
        terms = list(iter_terms(graph))
        for term in terms:
            write_term_document(graph, ttl_path.stem, term, output_dir)
        total += len(terms)
        print(f"Done processing {ttl_path.name}: {len(terms)} term document(s).")

    print(f"Wrote {total} GraphRAG term document(s) to {output_dir}.")


if __name__ == "__main__":
    main()
