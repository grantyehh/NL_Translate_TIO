"""
Train TransE on TIO triples and precompute OpenAI text embeddings per entity.

Usage (from project root):
  python -m kge.train

Requires: GRAPHRAG_API_KEY or OPENAI_API_KEY for text embeddings.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
from dotenv import load_dotenv
from openai import OpenAI
from pykeen.pipeline import pipeline
from pykeen.triples import TriplesFactory

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from kge.paths import (  # noqa: E402
    ENTITY_IDS_JSON,
    ENTITY_KGE_EMB_NPY,
    ENTITY_TEXT_EMB_NPY,
    KGE_DATA_DIR,
    MANIFEST_JSON,
    TRIPLES_TSV,
)
from kge.tio_triples import build_entity_descriptions, extract_triples_for_kge  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env")


def _write_triples_tsv(rows: list[tuple[str, str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for h, r, t in rows:
            f.write(f"{h}\t{r}\t{t}\n")


def _embed_texts_openai(
    client: OpenAI, texts: list[str], model: str, batch_size: int = 64
) -> np.ndarray:
    """Return (N, dim) float32, L2-normalized for cosine similarity."""
    def _clean_text(s: str) -> str:
        cleaned = "".join(ch if ch >= " " or ch in ("\n", "\t", "\r") else " " for ch in str(s))
        cleaned = cleaned.strip()
        return cleaned or "unknown ontology term"

    cleaned_texts = [_clean_text(t)[:8000] for t in texts]
    all_vecs: list[list[float]] = []
    for i in range(0, len(cleaned_texts), batch_size):
        batch = cleaned_texts[i : i + batch_size]
        try:
            resp = client.embeddings.create(model=model, input=batch)
            by_idx = sorted(enumerate(resp.data), key=lambda x: x[1].index)
            for _, item in by_idx:
                all_vecs.append(item.embedding)
        except Exception:
            # Recover by embedding each text separately to isolate bad input.
            for one in batch:
                resp = client.embeddings.create(model=model, input=one)
                all_vecs.append(resp.data[0].embedding)
    arr = np.asarray(all_vecs, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return arr / norms


def train_trans_e(
    triples: list[tuple[str, str, str]],
    embedding_dim: int,
    num_epochs: int,
    batch_size: int,
    lr: float,
    random_seed: int,
) -> tuple[np.ndarray, list[str]]:
    """Run PyKEEN TransE; return (L2-normalized entity matrix, entity_ids by index)."""
    arr = np.asarray(triples, dtype=object)
    tf = TriplesFactory.from_labeled_triples(arr)
    result = pipeline(
        training=tf,
        testing=tf,
        model="TransE",
        model_kwargs=dict(embedding_dim=embedding_dim),
        training_kwargs=dict(num_epochs=num_epochs, batch_size=batch_size),
        optimizer_kwargs=dict(lr=lr),
        random_seed=random_seed,
    )
    model = result.model
    n = model.num_entities
    ids = torch.arange(n, dtype=torch.long)
    emb = model.entity_representations[0](indices=ids).detach().cpu().numpy().astype(np.float32)
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    emb = emb / norms

    id_to_uri = {v: k for k, v in tf.entity_to_id.items()}
    entity_ids = [id_to_uri[i] for i in range(n)]
    return emb, entity_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Train KGE + entity text embeddings for TIO.")
    parser.add_argument("--embedding-dim", type=int, default=128)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--embedding-model",
        default="text-embedding-ada-002",
        help="OpenAI embedding model (match GraphRAG settings.yaml if possible).",
    )
    parser.add_argument("--skip-text-embeddings", action="store_true")
    args = parser.parse_args()

    triples = extract_triples_for_kge()
    if len(triples) < 3:
        raise SystemExit("Too few triples extracted; check ontology path and TTL files.")

    KGE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    _write_triples_tsv(triples, TRIPLES_TSV)
    print(f"Wrote {len(triples)} triples to {TRIPLES_TSV}")

    kge_emb, entity_ids = train_trans_e(
        triples,
        embedding_dim=args.embedding_dim,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        random_seed=args.seed,
    )

    with open(ENTITY_IDS_JSON, "w", encoding="utf-8") as f:
        json.dump(entity_ids, f, ensure_ascii=False, indent=2)
    np.save(ENTITY_KGE_EMB_NPY, kge_emb)

    manifest = {
        "model": "TransE",
        "embedding_dim": args.embedding_dim,
        "num_entities": len(entity_ids),
        "num_triples": len(triples),
        "epochs": args.epochs,
        "text_embedding_model": args.embedding_model,
    }
    with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved KGE embeddings: {ENTITY_KGE_EMB_NPY} ({kge_emb.shape})")

    if args.skip_text_embeddings:
        print("Skipped text embeddings (--skip-text-embeddings).")
    else:
        api_key = os.getenv("GRAPHRAG_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print(
                "Warning: GRAPHRAG_API_KEY / OPENAI_API_KEY not set; "
                "skipping text embeddings. Hybrid KGE context in nl_to_tio.py stays empty "
                "until you set the key and re-run this script (without --skip-text-embeddings)."
            )
        else:
            client = OpenAI(api_key=api_key)
            desc_map = build_entity_descriptions(entity_ids)
            texts = [desc_map[e][:8000] for e in entity_ids]
            text_emb = _embed_texts_openai(client, texts, args.embedding_model)
            np.save(ENTITY_TEXT_EMB_NPY, text_emb)
            print(f"Saved text embeddings: {ENTITY_TEXT_EMB_NPY} ({text_emb.shape})")


if __name__ == "__main__":
    main()
