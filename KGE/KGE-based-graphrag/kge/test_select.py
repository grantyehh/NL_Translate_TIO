import json
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent           # KGE/KGE-based-graphrag
sys.path.insert(0, str(EXP))
from kge.paths import ENTITY_IDS_JSON, TRIPLES_TSV, PROJECT_ROOT
from kge import select

TIO = "http://tio.models.tmforum.org/tio/v3.6.0/"
LATENCY = TIO + "EnterpriseVpnSlaOntology/latency"

def _real_triples():
    rows = []
    for line in TRIPLES_TSV.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            rows.append(tuple(parts))
    return rows

def test_transe_expand_returns_only_real_entities():
    out = select.transe_expand([LATENCY], top_k=8)
    eids = set(json.load(open(ENTITY_IDS_JSON, encoding="utf-8")))
    assert out, "expected some expansion for a seed that occurs in triples"
    assert all(u in eids for u in out)                 # never fabricated entities
    rows = _real_triples()
    mates = {h for h, r, t in rows if t == LATENCY} | {t for h, r, t in rows if h == LATENCY}
    assert set(out) <= mates                           # every result co-occurs in a REAL triple with the seed
    assert LATENCY not in out                           # seed itself excluded

def test_transe_expand_empty_for_unknown_seed():
    assert select.transe_expand(["http://example.org/not-an-entity"], top_k=8) == []
