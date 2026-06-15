import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kge import retrieve

def test_misuse_functions_removed():
    for gone in ("predict_likely_triples", "format_grounded_kge_context",
                 "format_kge_context_for_prompt", "get_kge_ranked_entities",
                 "score_link_predictions"):
        assert not hasattr(retrieve, gone), f"{gone} should be removed"

def test_loaders_and_helpers_kept():
    for kept in ("_load_arrays", "_load_kge_link_arrays", "_load_triple_rows",
                 "_embed_query", "trans_e_score", "kge_ready",
                 "kge_link_prediction_ready", "_uri_to_curie"):
        assert hasattr(retrieve, kept), f"{kept} must remain"
