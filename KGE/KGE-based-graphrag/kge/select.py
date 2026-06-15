from __future__ import annotations

import sys

from kge.paths import PROJECT_ROOT
from kge.retrieve import (
    _load_kge_link_arrays,
    _load_triple_rows,
    kge_link_prediction_ready,
    trans_e_score,
)

# Reuse GraphRAG's shared output-contract modules (later tasks).
sys.path.insert(0, str(PROJECT_ROOT / "GraphRag"))


def transe_expand(seed_uris: list[str], *, top_k: int = 8) -> list[str]:
    """Expand seeds to related entities by ranking the REAL triples that contain
    a seed (TransE plausibility -‖h+r−t‖). Returns entities from those real
    triples only — never fabricates a triple or an entity."""
    if not seed_uris or not kge_link_prediction_ready():
        return []
    entity_ids, relation_ids, entity_kge, relation_kge = _load_kge_link_arrays()
    eidx = {u: i for i, u in enumerate(entity_ids)}
    ridx = {u: i for i, u in enumerate(relation_ids)}
    seeds = set(seed_uris)
    scored: list[tuple[float, str, str]] = []
    for h, r, t in _load_triple_rows():
        if (h in seeds or t in seeds) and h in eidx and r in ridx and t in eidx:
            s = trans_e_score(entity_kge[eidx[h]], relation_kge[ridx[r]], entity_kge[eidx[t]])
            scored.append((s, h, t))
    scored.sort(key=lambda x: (-x[0], x[1], x[2]))
    out: list[str] = []
    for _s, h, t in scored[:top_k]:
        for e in (h, t):
            if e not in seeds and e not in out:
                out.append(e)
    return out
