import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evsla_prompt import build_evsla_system_prompt

def test_structure_only_keeps_skeleton_withholds_vocab():
    p = build_evsla_system_prompt("TC001", profile="structure_only")
    assert "PropertyExpectation" in p or "intentElements" in p
    assert "log:Condition" in p
    assert "evsla:latency" not in p
    assert "evsla:p95" not in p
    assert "quan:smaller" not in p
    assert "@prefix evsla:" not in p

def test_structure_only_is_retrieval_mode_independent():
    a = build_evsla_system_prompt("TC001", retrieval_mode="KGE", profile="structure_only")
    b = build_evsla_system_prompt("TC001", retrieval_mode="GraphRAG", profile="structure_only")
    c = build_evsla_system_prompt("TC001", retrieval_mode=None, profile="structure_only")
    assert a == b == c

def test_strong_profile_still_has_full_knowledge():
    p = build_evsla_system_prompt("TC001", profile="strong")
    assert "evsla:latency" in p

import json

def test_skeleton_few_shot_has_no_evsla_vocabulary():
    path = Path(__file__).resolve().parent.parent / "few_shot_structure_only.json"
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert data.get("examples")
    for bad in ("evsla:latency", "evsla:p95", "quan:smaller", "EnterpriseVpnSlaOntology"):
        assert bad not in raw
    assert "PropertyExpectation" in raw or "intentElements" in raw
