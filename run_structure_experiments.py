#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from openai_config import embedding_model


ROOT = Path(__file__).resolve().parent
PHASE1_DIR = ROOT / "phase1"
OUTPUT_QUALITY_DIR = PHASE1_DIR / "output_quality"
TOKEN_USAGE_DIR = PHASE1_DIR / "token_usage"

SEM_DIMS = [
    "metric",
    "threshold",
    "statistic",
    "scope",
    "measurement_method",
    "time_window",
    "operator",
    "tenant",
    "topology",
    "contract",
    "precision",
]


@dataclass(frozen=True)
class ExperimentLine:
    label: str
    experiment: str
    script: Path
    prompt_profile: str
    report: Path


LINES = [
    ExperimentLine(
        label="LLM ceiling",
        experiment="llm_only",
        script=Path("LLM-only/nl_to_tio.py"),
        prompt_profile="strong",
        report=PHASE1_DIR / "phase1_llm_only.json",
    ),
    ExperimentLine(
        label="LLM baseline",
        experiment="llm_only_structure",
        script=Path("LLM-only/nl_to_tio.py"),
        prompt_profile="structure_only",
        report=PHASE1_DIR / "phase1_llm_only_structure.json",
    ),
    ExperimentLine(
        label="GraphRAG",
        experiment="graphrag_structure",
        script=Path("GraphRag/nl_to_tio.py"),
        prompt_profile="structure_only",
        report=PHASE1_DIR / "phase1_graphrag_structure.json",
    ),
    ExperimentLine(
        label="KGE",
        experiment="kge_structure",
        script=Path("KGE/KGE-based-graphrag/nl_to_tio.py"),
        prompt_profile="structure_only",
        report=PHASE1_DIR / "phase1_kge_structure.json",
    ),
]


def run_command(cmd: list[str | Path], cwd: Path) -> None:
    printable = " ".join(str(part) for part in cmd)
    print(f"\n[{cwd}] $ {printable}", flush=True)
    subprocess.run([str(part) for part in cmd], cwd=cwd, check=True)


def generation_command(line: ExperimentLine, test_cases: Path) -> list[str | Path]:
    return [
        sys.executable,
        ROOT / line.script,
        "--test-cases",
        test_cases.resolve(),
        "--prompt-profile",
        line.prompt_profile,
    ]


def evaluate_command(line: ExperimentLine, test_cases: Path) -> list[str | Path]:
    return [
        sys.executable,
        ROOT / "evaluate_ttl.py",
        line.experiment,
        "--test-cases",
        test_cases.resolve(),
    ]


def run_optional_prep(*, rebuild_graphrag_index: bool, retrain_kge: bool) -> None:
    if rebuild_graphrag_index:
        run_command(
            [
                sys.executable,
                ROOT / "GraphRag" / "build_index.py",
                "--output-dir",
                ROOT / "GraphRag" / "index",
                "--usage-experiment",
                "graphrag_structure",
            ],
            ROOT,
        )
    if retrain_kge:
        run_command(
            [
                sys.executable,
                "-m",
                "kge.train",
                "--embedding-model",
                embedding_model("text-embedding-3-small"),
                "--usage-experiment",
                "kge_structure",
            ],
            ROOT / "KGE" / "KGE-based-graphrag",
        )


def load_report(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Report must be a JSON array: {path}")
    return [row for row in data if isinstance(row, dict)]


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def coerce_number(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def aggregate_accuracy(rows: list[dict]) -> dict:
    n = len(rows)
    semantic_rows = [row.get("semantic") or {} for row in rows]
    dims = {
        dim: mean(
            coerce_number((sem.get("dimensions") or {}).get(dim))
            for sem in semantic_rows
        )
        for dim in SEM_DIMS
    }
    return {
        "cases": n,
        "parse_ok_rate": mean(1.0 if row.get("parse_ok") else 0.0 for row in rows),
        "avg_coverage": mean(coerce_number(row.get("expected_coverage_ratio")) for row in rows),
        "avg_triples": mean(coerce_number(row.get("triple_count")) for row in rows),
        "unknown_predicates": sum(len(row.get("unknown_predicates") or []) for row in rows),
        "unknown_types": sum(len(row.get("unknown_types") or []) for row in rows),
        "semantic_composite": mean(coerce_number(sem.get("composite")) for sem in semantic_rows),
        "dimensions": dims,
    }


def write_accuracy_summary(reports: dict[str, Path], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    loaded = {line.experiment: load_report(reports[line.experiment]) for line in LINES}
    metrics = {line.experiment: aggregate_accuracy(loaded[line.experiment]) for line in LINES}

    lines: list[str] = []
    lines.append("Structure Four-Line Accuracy Summary")
    lines.append("------------------------------------")
    lines.append("Reports:")
    for line in LINES:
        lines.append(f"- {line.label}: {reports[line.experiment]}")
    lines.append("")
    lines.append(
        f"{'Experiment':14} | {'Cases':5} | {'Parse OK':8} | {'Coverage':8} | "
        f"{'Composite':9} | {'Triples':7} | {'Unk pred':8} | {'Unk type':8}"
    )
    lines.append("-" * 92)
    for line in LINES:
        m = metrics[line.experiment]
        lines.append(
            f"{line.label:14} | "
            f"{m['cases']:5d} | "
            f"{m['parse_ok_rate'] * 100:7.2f}% | "
            f"{m['avg_coverage']:8.4f} | "
            f"{m['semantic_composite']:9.4f} | "
            f"{m['avg_triples']:7.2f} | "
            f"{m['unknown_predicates']:8d} | "
            f"{m['unknown_types']:8d}"
        )
    lines.append("")
    lines.append("Semantic Dimensions")
    lines.append("-------------------")
    header = f"{'Experiment':14} | " + " | ".join(f"{dim:>18}" for dim in SEM_DIMS)
    lines.append(header)
    lines.append("-" * len(header))
    for line in LINES:
        dims = metrics[line.experiment]["dimensions"]
        lines.append(
            f"{line.label:14} | "
            + " | ".join(f"{dims[dim]:18.2f}" for dim in SEM_DIMS)
        )

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved accuracy summary to: {out_path}")


def write_token_summary(out_path: Path) -> None:
    run_command(
        [
            sys.executable,
            ROOT / "compare_token_usage.py",
            "--variant",
            "structure",
            "--out",
            str(out_path),
        ],
        ROOT,
    )


def run_workflow(
    *,
    test_cases: Path,
    eval_only: bool = False,
    rebuild_graphrag_index: bool = False,
    retrain_kge: bool = False,
    accuracy_out: Path | None = None,
    token_out: Path | None = None,
) -> None:
    PHASE1_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_USAGE_DIR.mkdir(parents=True, exist_ok=True)

    if not eval_only:
        run_optional_prep(
            rebuild_graphrag_index=rebuild_graphrag_index,
            retrain_kge=retrain_kge,
        )
        for line in LINES:
            run_command(generation_command(line, test_cases), ROOT)

    for line in LINES:
        run_command(evaluate_command(line, test_cases), ROOT)

    reports = {line.experiment: line.report for line in LINES}
    write_accuracy_summary(
        reports,
        accuracy_out or OUTPUT_QUALITY_DIR / "compare_structure_four_way.txt",
    )
    write_token_summary(
        token_out or TOKEN_USAGE_DIR / "compare_token_usage_structure.txt",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the structure-regime four-line workflow: LLM ceiling, "
            "LLM baseline/floor, GraphRAG-structure, and KGE-structure."
        )
    )
    parser.add_argument(
        "--test-cases",
        type=Path,
        default=ROOT / "test_cases_40.json",
        help="Test cases JSON (default: test_cases_40.json).",
    )
    parser.add_argument(
        "--eval-only",
        action="store_true",
        help="Skip generation and only recompute evaluation + summaries.",
    )
    parser.add_argument(
        "--rebuild-graphrag-index",
        action="store_true",
        help="Rebuild GraphRAG resource embeddings before generation and record prep tokens.",
    )
    parser.add_argument(
        "--retrain-kge",
        action="store_true",
        help="Retrain KGE artifacts before generation and record prep tokens.",
    )
    parser.add_argument(
        "--accuracy-out",
        type=Path,
        default=None,
        help="Accuracy summary path (default: phase1/output_quality/compare_structure_four_way.txt).",
    )
    parser.add_argument(
        "--token-out",
        type=Path,
        default=None,
        help="Token summary path (default: phase1/token_usage/compare_token_usage_structure.txt).",
    )
    args = parser.parse_args(argv)

    test_cases = args.test_cases.resolve()
    if not test_cases.is_file():
        raise SystemExit(f"Missing test cases file: {test_cases}")

    run_workflow(
        test_cases=test_cases,
        eval_only=args.eval_only,
        rebuild_graphrag_index=args.rebuild_graphrag_index,
        retrain_kge=args.retrain_kge,
        accuracy_out=args.accuracy_out.resolve() if args.accuracy_out else None,
        token_out=args.token_out.resolve() if args.token_out else None,
    )
    print("\nCompleted structure four-line workflow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
