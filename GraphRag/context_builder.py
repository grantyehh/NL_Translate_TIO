from __future__ import annotations

TIO = "http://tio.models.tmforum.org/tio/v3.6.0/"
PREFIXES = [
    ("evsla", TIO + "EnterpriseVpnSlaOntology/"),
    ("icm", TIO + "IntentCommonModel/"),
    ("quan", TIO + "QuantityOntology/"),
    ("met", TIO + "MetricsAndObservations/"),
    ("log", TIO + "LogicalOperators/"),
    ("fun", TIO + "FunctionOntology/"),
    ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
    ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
]


def serialize_context(
    grounded: list[tuple[str, str, str, str]],
    relations: list[tuple[str, str, str]],
    reached_vocab: dict[str, list[str]],
    conventions: dict | None = None,
) -> str:
    lines = ["### Canonical prefixes"]
    lines += [f"{p}: <{ns}>" for p, ns in PREFIXES]
    lines += ["", "### Grounded terms (NL concept -> ontology term)"]
    for _term, curie, typ, gloss in grounded:
        lines.append(f"- {curie} ({typ}) -- {gloss}")
    lines += ["", "### Connective relations (how an SLA expectation wires together)"]
    for s, p, o in relations:
        lines.append(f"- {s} {p} -> {o}")
    if reached_vocab:
        lines += ["", "### Closed vocabulary per reached role (pick one per slot)"]
        for role in sorted(reached_vocab):
            lines.append(f"- {role}: {', '.join(reached_vocab[role])}")
    if conventions:
        lines += ["", "### Conventions (apply when the NL gives no explicit cue)"]
        md = conventions.get("method_defaults") or {}
        if md:
            lines.append("- Measurement method default per metric:")
            for metric in sorted(md):
                lines.append(f"  - {metric} -> {md[metric]}")
        if conventions.get("window_default"):
            lines.append(f"- Time window default: {conventions['window_default']}")
        wt = conventions.get("window_triggers") or {}
        for label in sorted(wt):
            lines.append(f"  - if NL mentions 「{label}」 use {wt[label]}")
    return "\n".join(lines) + "\n"


def guard_tokens(
    items: list[tuple[str, int]], budget: int
) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    """Keep highest-priority items (list order = priority) within token budget;
    drop lowest-priority complete items. Never truncates an item."""
    kept: list[tuple[str, int]] = []
    total = 0
    for text, toks in items:
        if total + toks <= budget:
            kept.append((text, toks))
            total += toks
        else:
            break
    dropped = items[len(kept):]
    return kept, dropped
