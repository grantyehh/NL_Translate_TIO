from __future__ import annotations

from pathlib import Path

from rdflib import Graph

# Several TIO v3.6.0 TTL files omit prefix declarations that they reference.
# Inject the missing bindings when they are absent so rdflib can parse them.
_MISSING_PREFIXES = {
    "icm": "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/",
    "imo": "http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/",
}


def _read_with_prefix_fix(ttl_path: Path) -> str:
    """Return the file content with any missing @prefix declarations prepended."""
    content = ttl_path.read_text(encoding="utf-8")
    injection = "".join(
        f"@prefix {pfx}: <{uri}> .\n"
        for pfx, uri in _MISSING_PREFIXES.items()
        if f"@prefix {pfx}:" not in content
    )
    return injection + content


def load_ontology(ttl_dir: Path) -> Graph:
    """Load and merge all .ttl files in ttl_dir into a single rdflib Graph."""
    g = Graph()
    for ttl_path in sorted(Path(ttl_dir).glob("*.ttl")):
        g.parse(data=_read_with_prefix_fix(ttl_path), format="turtle")
    return g
