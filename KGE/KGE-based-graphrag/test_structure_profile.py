import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import importlib
nl_to_tio = importlib.import_module("nl_to_tio")

def test_kge_structure_experiment_key():
    nl_to_tio.PROFILE = "structure_only"
    p = nl_to_tio.output_path_for_case(Path(nl_to_tio.__file__).resolve().parent, "TC001")
    assert p.parent.name == "kge_structure"
    nl_to_tio.PROFILE = "strong"
    assert nl_to_tio.output_path_for_case(Path(nl_to_tio.__file__).resolve().parent, "TC001").parent.name == "kge"

def test_nl_to_tio_uses_canonical_kge_retrieval():
    import inspect, nl_to_tio
    src = inspect.getsource(nl_to_tio)
    assert "build_kge_context" in src
    assert "format_kge_context_for_prompt" not in src
