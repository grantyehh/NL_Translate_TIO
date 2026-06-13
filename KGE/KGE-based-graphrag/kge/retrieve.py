"""
KGE retrieval: text grounding + TransE neighborhood expansion and link prediction.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import sys
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_REPO_ROOT = _PROJECT_ROOT.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kge.paths import (  # noqa: E402
    ENTITY_IDS_JSON,
    ENTITY_KGE_EMB_NPY,
    ENTITY_TEXT_EMB_NPY,
    MANIFEST_JSON,
    RELATION_IDS_JSON,
    RELATION_KGE_EMB_NPY,
    TRIPLES_TSV,
)
from kge.tio_triples import entity_text_description, load_merged_ontology_graph  # noqa: E402
from token_usage import record_usage  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env")

TIO_PREFIXES = {
    "evsla": "http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/",
    "icm": "http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/",
    "imo": "http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/",
    "fun": "http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/",
    "log": "http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/",
    "math": "http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions/",
    "mf": "http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions",
    "set": "http://tio.models.tmforum.org/tio/v3.6.0/SetOperators/",
    "met": "http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/",
    "quan": "http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/",
    "ig": "http://tio.models.tmforum.org/tio/v3.6.0/IntentGuaranteeOntology/",
    "insp": "http://tio.models.tmforum.org/tio/v3.6.0/IntentSpecification/",
    "pbi": "http://tio.models.tmforum.org/tio/v3.6.0/ProposalBestIntent/",
    "pro": "http://tio.models.tmforum.org/tio/v3.6.0/IntentProbing/",
}

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_SUBCLASS_OF = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
RDFS_SUBPROPERTY_OF = "http://www.w3.org/2000/01/rdf-schema#subPropertyOf"
RDFS_DOMAIN = "http://www.w3.org/2000/01/rdf-schema#domain"
RDFS_RANGE = "http://www.w3.org/2000/01/rdf-schema#range"
RDFS_MEMBER = "http://www.w3.org/2000/01/rdf-schema#member"

# Retrieval hyperparameters (tuned for ontology size)
TEXT_TOP_SEED = 8
KGE_NEIGHBORS_PER_SEED = 14
MAX_TERMS_IN_PROMPT = 45
MAX_PREDICTED_TRIPLES = 18


@dataclass(frozen=True)
class LinkPrediction:
    head_uri: str
    relation_uri: str
    tail_uri: str
    score: float


def _uri_to_curie(uri: str) -> str:
    for prefix, base in TIO_PREFIXES.items():
        if uri.startswith(base):
            return f"{prefix}:{uri[len(base):]}"
    return uri


def kge_ready() -> bool:
    """True when KGE + text embeddings exist for retrieval."""
    return (
        ENTITY_IDS_JSON.is_file()
        and ENTITY_KGE_EMB_NPY.is_file()
        and ENTITY_TEXT_EMB_NPY.is_file()
    )


def kge_link_prediction_ready() -> bool:
    """True when TransE entity and relation artifacts exist."""
    return (
        ENTITY_IDS_JSON.is_file()
        and ENTITY_KGE_EMB_NPY.is_file()
        and RELATION_IDS_JSON.is_file()
        and RELATION_KGE_EMB_NPY.is_file()
    )


def _artifacts_ready() -> bool:
    return kge_ready()


def _load_arrays():
    with open(ENTITY_IDS_JSON, "r", encoding="utf-8") as f:
        entity_ids: list[str] = json.load(f)
    kge = np.load(ENTITY_KGE_EMB_NPY)
    text_e = np.load(ENTITY_TEXT_EMB_NPY)
    if len(entity_ids) != kge.shape[0] or len(entity_ids) != text_e.shape[0]:
        raise ValueError("entity_ids length does not match embedding matrices")
    return entity_ids, kge.astype(np.float32), text_e.astype(np.float32)


def _load_kge_link_arrays():
    with open(ENTITY_IDS_JSON, "r", encoding="utf-8") as f:
        entity_ids: list[str] = json.load(f)
    with open(RELATION_IDS_JSON, "r", encoding="utf-8") as f:
        relation_ids: list[str] = json.load(f)
    entity_kge = np.load(ENTITY_KGE_EMB_NPY).astype(np.float32)
    relation_kge = np.load(RELATION_KGE_EMB_NPY).astype(np.float32)
    if len(entity_ids) != entity_kge.shape[0]:
        raise ValueError("entity_ids length does not match entity KGE matrix")
    if len(relation_ids) != relation_kge.shape[0]:
        raise ValueError("relation_ids length does not match relation KGE matrix")
    return entity_ids, relation_ids, entity_kge, relation_kge


def _load_triple_rows() -> list[tuple[str, str, str]]:
    if not TRIPLES_TSV.is_file():
        return []
    rows: list[tuple[str, str, str]] = []
    with open(TRIPLES_TSV, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 3:
                rows.append((parts[0], parts[1], parts[2]))
    return rows


def _embed_query(client: OpenAI, text: str, model: str) -> np.ndarray:
    resp = client.embeddings.create(model=model, input=text[:8000])
    case_id = os.getenv("KGE_ACTIVE_CASE_ID")
    record_usage(
        _REPO_ROOT / "phase1" / "token_usage" / "token_usage_kge.json",
        experiment="kge",
        ledger="online",
        case_id=case_id,
        stage="retrieval_embedding",
        model=model,
        api="embeddings",
        response=resp,
    )
    v = np.asarray(resp.data[0].embedding, dtype=np.float32)
    n = np.linalg.norm(v)
    if n < 1e-12:
        return v
    return v / n


def _top_k_indices(scores: np.ndarray, k: int, exclude: set[int] | None = None) -> list[int]:
    if exclude is None:
        exclude = set()
    # Partial sort
    idx = np.argpartition(-scores, min(k + len(exclude), len(scores) - 1))[: k + len(exclude)]
    idx = idx[np.argsort(-scores[idx])]
    out: list[int] = []
    for i in idx.tolist():
        if i in exclude:
            continue
        out.append(i)
        if len(out) >= k:
            break
    return out


def trans_e_score(head_vec: np.ndarray, relation_vec: np.ndarray, tail_vec: np.ndarray) -> float:
    """Return a TransE score where larger is better."""
    return -float(np.linalg.norm(head_vec + relation_vec - tail_vec, ord=2))


def score_link_predictions(
    head_uri: str,
    entity_ids: list[str],
    relation_ids: list[str],
    entity_kge: np.ndarray,
    relation_kge: np.ndarray,
    *,
    relation_whitelist: set[str] | None = None,
    candidate_tail_uris: set[str] | None = None,
    top_k: int = MAX_PREDICTED_TRIPLES,
) -> list[LinkPrediction]:
    """
    Score candidate (head, relation, tail) triples with TransE.

    The caller supplies the relation whitelist and tail candidates, so prediction
    is constrained by ontology-derived filters instead of test-case ground truth.
    """
    entity_index = {uri: i for i, uri in enumerate(entity_ids)}
    relation_index = {uri: i for i, uri in enumerate(relation_ids)}
    if head_uri not in entity_index:
        return []

    allowed_relations = relation_whitelist or set(relation_ids)
    allowed_relation_indices = [
        relation_index[uri] for uri in relation_ids if uri in relation_index and uri in allowed_relations
    ]
    if candidate_tail_uris is None:
        candidate_tail_uris = set(entity_ids)
    candidate_tail_indices = [
        entity_index[uri]
        for uri in candidate_tail_uris
        if uri in entity_index and uri != head_uri
    ]

    h_idx = entity_index[head_uri]
    h_vec = entity_kge[h_idx]
    scored: list[LinkPrediction] = []
    for r_idx in allowed_relation_indices:
        relation_uri = relation_ids[r_idx]
        r_vec = relation_kge[r_idx]
        for t_idx in candidate_tail_indices:
            tail_uri = entity_ids[t_idx]
            scored.append(
                LinkPrediction(
                    head_uri=head_uri,
                    relation_uri=relation_uri,
                    tail_uri=tail_uri,
                    score=trans_e_score(h_vec, r_vec, entity_kge[t_idx]),
                )
            )

    scored.sort(key=lambda p: p.score, reverse=True)
    return scored[:top_k]


def _default_relation_whitelist(relation_ids: list[str]) -> set[str]:
    structural = {RDF_TYPE, RDFS_SUBCLASS_OF, RDFS_SUBPROPERTY_OF, RDFS_DOMAIN, RDFS_RANGE}
    out: set[str] = set()
    for uri in relation_ids:
        if uri in structural:
            out.add(uri)
        elif uri.startswith("http://tio.models.tmforum.org/tio/v3.6.0/"):
            out.add(uri)
    out.discard(RDFS_MEMBER)
    return out


def _candidate_tail_uris(
    entity_ids: list[str],
    grounded_uris: list[str],
    triple_rows: list[tuple[str, str, str]],
) -> set[str]:
    candidates = set(grounded_uris)
    mentioned = set(grounded_uris)
    for h, _r, t in triple_rows:
        if h in mentioned or t in mentioned:
            candidates.add(h)
            candidates.add(t)
    return candidates or set(entity_ids)


def predict_likely_triples(
    grounded_uris: list[str],
    *,
    top_k: int = MAX_PREDICTED_TRIPLES,
) -> list[LinkPrediction]:
    """Predict likely ontology triples for grounded URIs using saved TransE artifacts."""
    if not grounded_uris or not kge_link_prediction_ready():
        return []

    entity_ids, relation_ids, entity_kge, relation_kge = _load_kge_link_arrays()
    triples = _load_triple_rows()
    relation_whitelist = _default_relation_whitelist(relation_ids)
    candidate_tail_uris = _candidate_tail_uris(entity_ids, grounded_uris, triples)

    seen_existing = set(triples)
    predictions: list[LinkPrediction] = []
    for head_uri in grounded_uris:
        for pred in score_link_predictions(
            head_uri,
            entity_ids,
            relation_ids,
            entity_kge,
            relation_kge,
            relation_whitelist=relation_whitelist,
            candidate_tail_uris=candidate_tail_uris,
            top_k=top_k,
        ):
            if (pred.head_uri, pred.relation_uri, pred.tail_uri) in seen_existing:
                continue
            predictions.append(pred)

    dedup: dict[tuple[str, str, str], LinkPrediction] = {}
    for pred in predictions:
        key = (pred.head_uri, pred.relation_uri, pred.tail_uri)
        if key not in dedup or pred.score > dedup[key].score:
            dedup[key] = pred

    ordered = sorted(dedup.values(), key=lambda p: p.score, reverse=True)
    return ordered[:top_k]


def format_grounded_kge_context(
    grounded: list[tuple[str, str, str, str]],
    predictions: list[LinkPrediction],
) -> str:
    """Format grounded URIs and TransE-predicted triples for the LLM prompt."""
    if not grounded and not predictions:
        return ""

    lines = [
        "### KGE grounded URI and link prediction context",
        "Use these as structural hints, not as test-case answers.",
        "",
    ]
    if grounded:
        lines.extend(["Grounded URIs:"])
        for curie, uri, tag, description in grounded:
            desc = description[:400]
            lines.append(f"- [{tag}] {curie} <{uri}> — {desc}")
        lines.append("")

    if predictions:
        lines.extend(["Predicted likely triples:"])
        for pred in predictions:
            h = _uri_to_curie(pred.head_uri)
            r = _uri_to_curie(pred.relation_uri)
            t = _uri_to_curie(pred.tail_uri)
            lines.append(f"- {h} {r} {t} (TransE score={pred.score:.4f})")

    return "\n".join(lines) + "\n"


def get_kge_ranked_entities(
    nl_query: str,
    *,
    text_top_seed: int = TEXT_TOP_SEED,
    kge_neighbors_per_seed: int = KGE_NEIGHBORS_PER_SEED,
    max_terms: int = MAX_TERMS_IN_PROMPT,
    embedding_model: str | None = None,
    case_id: str | None = None,
) -> list[tuple[str, str, str]]:
    """
    Return list of (curie, full_iri, reason_tag) for prompt injection.
    reason_tag: 'text' | 'kge_neighbor'
    """
    if not _artifacts_ready():
        return []

    manifest_model = None
    if MANIFEST_JSON.is_file():
        with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
            manifest_model = json.load(f).get("text_embedding_model")

    model = embedding_model or manifest_model or "text-embedding-ada-002"

    api_key = os.getenv("GRAPHRAG_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []

    entity_ids, kge_emb, text_emb = _load_arrays()
    client = OpenAI(api_key=api_key)
    previous_case_id = os.getenv("KGE_ACTIVE_CASE_ID")
    if case_id:
        os.environ["KGE_ACTIVE_CASE_ID"] = case_id
    try:
        q = _embed_query(client, nl_query, model)
    finally:
        if case_id:
            if previous_case_id is None:
                os.environ.pop("KGE_ACTIVE_CASE_ID", None)
            else:
                os.environ["KGE_ACTIVE_CASE_ID"] = previous_case_id

    text_scores = text_emb @ q
    seed_indices = _top_k_indices(text_scores, text_top_seed)

    selected: dict[int, str] = {i: "text" for i in seed_indices}

    # KGE neighborhood expansion from each seed (cosine in entity embedding space)
    for si in seed_indices:
        ref = kge_emb[si]
        sims = kge_emb @ ref
        neigh = _top_k_indices(sims, kge_neighbors_per_seed + 1, exclude={si})
        for ni in neigh:
            if ni not in selected:
                selected[ni] = "kge_neighbor"

    seeds_ordered = sorted(seed_indices, key=lambda x: -text_scores[x])
    seed_set = set(seed_indices)
    kge_only = [i for i in selected if i not in seed_set]
    if kge_only and seed_indices:
        seed_mat = kge_emb[np.array(seed_indices)]
        kge_only_sorted = sorted(
            kge_only,
            key=lambda x: float(np.max(seed_mat @ kge_emb[x])),
            reverse=True,
        )
    elif kge_only:
        kge_only_sorted = sorted(kge_only, key=lambda x: -text_scores[x])
    else:
        kge_only_sorted = []

    ordered = seeds_ordered + kge_only_sorted

    seen: set[int] = set()
    final_order: list[int] = []
    for i in ordered:
        if i not in seen and i < len(entity_ids):
            seen.add(i)
            final_order.append(i)
        if len(final_order) >= max_terms:
            break

    rows: list[tuple[str, str, str]] = []
    for i in final_order:
        uri = entity_ids[i]
        curie = _uri_to_curie(uri)
        tag = selected.get(i, "kge_neighbor")
        rows.append((curie, uri, tag))

    return rows


def format_kge_context_for_prompt(nl_query: str, case_id: str | None = None) -> str:
    """
    Human-readable block for LLM: suggested TIO terms from hybrid KGE retrieval.
    Returns empty string if artifacts or API are unavailable.
    """
    try:
        ranked = get_kge_ranked_entities(nl_query, case_id=case_id)
    except Exception:
        return ""

    if not ranked:
        return ""

    g = load_merged_ontology_graph()
    lines = [
        "### KGE-assisted term hints (TransE + text similarity; prefer official CURIEs below when applicable)",
        "",
    ]
    grounded: list[tuple[str, str, str, str]] = []
    for curie, uri, tag in ranked:
        short = entity_text_description(g, uri)[:400]
        grounded.append((curie, uri, tag, short))
        lines.append(f"- [{tag}] {curie} — {short}")

    predicted = predict_likely_triples([uri for _curie, uri, _tag in ranked])
    grounded_context = format_grounded_kge_context(grounded, predicted)
    if grounded_context:
        lines.append("")
        lines.append(grounded_context.rstrip())

    return "\n".join(lines) + "\n"
