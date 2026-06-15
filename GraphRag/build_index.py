from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ontology_graph import load_ontology
from resource_index import OntologyResource, build_resource_index

TTL_DIR = Path(__file__).resolve().parent.parent / "TM Forum Intent Ontology"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "index"
EMBED_MODEL = "text-embedding-3-small"


def write_resources_json(resources: list[OntologyResource], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([asdict(r) for r in resources], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _resource_text(r: OntologyResource) -> str:
    parts = list(r.labels) + list(r.alt_labels)
    if r.comment:
        parts.append(r.comment)
    return " ".join(parts) or r.curie


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build GraphRAG resource index.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true", help="Report status; never call API.")
    args = parser.parse_args(argv)

    resources = build_resource_index(load_ontology(TTL_DIR))
    emb_path = args.output_dir / "resource_embeddings.npy"
    if args.check:
        status = "ok" if emb_path.is_file() else "missing"
        print(f"index status: {status}; resources={len(resources)}; output-dir={args.output_dir}")
        if status == "missing":
            print(f"--if-stale: python GraphRag/build_index.py --output-dir {args.output_dir}")
        return 0

    write_resources_json(resources, args.output_dir / "resources.json")
    api_key = os.getenv("GRAPHRAG_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("No API key; wrote resources.json only (embeddings skipped).")
        return 0
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    texts = [_resource_text(r) for r in resources]
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    vecs = np.asarray([d.embedding for d in resp.data], dtype=np.float32)
    np.save(emb_path, vecs)
    (args.output_dir / "manifest.json").write_text(
        json.dumps(
            {"embedding_model": EMBED_MODEL, "num_resources": len(resources)},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Built index: {len(resources)} resources -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
