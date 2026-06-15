import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import evaluate_ttl

def test_structure_keys_registered():
    for key in ("graphrag_structure", "kge_structure", "llm_only_structure"):
        assert key in evaluate_ttl.EXPERIMENTS
        assert evaluate_ttl.EXPERIMENTS[key]["outputs_dir"].name == key
