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
from openai_config import create_embedding_client, embedding_model, load_project_env
from resource_index import OntologyResource, build_resource_index
from token_usage import record_usage, reset_usage_ledger

TTL_DIR = Path(__file__).resolve().parent.parent / "TM Forum Intent Ontology"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "index"
EMBED_MODEL = "text-embedding-3-small"
DEFAULT_USAGE_EXPERIMENT = "graphrag_structure"


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


def token_usage_path(experiment: str = DEFAULT_USAGE_EXPERIMENT) -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "phase1"
        / "token_usage"
        / f"token_usage_{experiment}.json"
    )


def main(argv: list[str] | None = None) -> int:
    load_project_env()

    parser = argparse.ArgumentParser(description="Build GraphRAG resource index.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true", help="Report status; never call API.")
    parser.add_argument(
        "--usage-experiment",
        default=DEFAULT_USAGE_EXPERIMENT,
        help="Experiment key for prep token ledger (default: graphrag_structure).",
    )
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
    try:
        client = create_embedding_client()
    except RuntimeError as e:
        print(f"{e}; wrote resources.json only (embeddings skipped).")
        return 0
    texts = [_resource_text(r) for r in resources]
    usage_path = token_usage_path(args.usage_experiment)
    reset_usage_ledger(usage_path, "prep")
    model = embedding_model(EMBED_MODEL)
    resp = client.embeddings.create(model=model, input=texts)
    record_usage(
        usage_path,
        experiment=args.usage_experiment,
        ledger="prep",
        case_id=None,
        stage="resource_index_embeddings",
        model=model,
        api="embeddings",
        response=resp,
    )
    vecs = np.asarray([d.embedding for d in resp.data], dtype=np.float32)
    np.save(emb_path, vecs)
    (args.output_dir / "manifest.json").write_text(
        json.dumps(
            {"embedding_model": model, "num_resources": len(resources)},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Built index: {len(resources)} resources -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
