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

def test_strong_profile_still_has_full_knowledge():
    p = build_evsla_system_prompt("TC001", profile="strong")
    assert "evsla:latency" in p
