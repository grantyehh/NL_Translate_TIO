"""KGE retrieval for TIO (TransE link prediction + text embeddings)."""

from kge.retrieve import (
    format_kge_context_for_prompt,
    get_kge_ranked_entities,
    kge_ready,
)

__all__ = [
    "format_kge_context_for_prompt",
    "get_kge_ranked_entities",
    "kge_ready",
]
