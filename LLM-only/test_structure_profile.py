import importlib.util
import sys
from pathlib import Path

# Load LLM-only nl_to_tio.py with a unique module name to avoid collision
# with GraphRag/nl_to_tio.py when pytest collects both directories together.
_MODULE_PATH = Path(__file__).resolve().parent / "nl_to_tio.py"

# Reuse the already-loaded module if test_nl_to_tio.py loaded it first.
if "llm_only_nl_to_tio" in sys.modules:
    nl_to_tio = sys.modules["llm_only_nl_to_tio"]
else:
    _spec = importlib.util.spec_from_file_location("llm_only_nl_to_tio", _MODULE_PATH)
    nl_to_tio = importlib.util.module_from_spec(_spec)
    sys.modules["llm_only_nl_to_tio"] = nl_to_tio
    _spec.loader.exec_module(nl_to_tio)


def test_llm_only_structure_experiment_key():
    nl_to_tio.PROFILE = "structure_only"
    p = nl_to_tio.output_path_for_case(Path(nl_to_tio.__file__).resolve().parent, "TC001")
    assert p.parent.name == "llm_only_structure"
    nl_to_tio.PROFILE = "strong"
    assert nl_to_tio.output_path_for_case(Path(nl_to_tio.__file__).resolve().parent, "TC001").parent.name == "llm_only"
