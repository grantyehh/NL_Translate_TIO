#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
COMPARE_SCRIPT = ROOT / "compare_reports.py"
TOKEN_COMPARE_SCRIPT = ROOT / "compare_token_usage.py"
PHASE1_EVALUATOR = ROOT / "evaluate_jsonld.py"
PHASE1_DIR = ROOT / "phase1"
OUTPUT_QUALITY_DIR = PHASE1_DIR / "output_quality"
TOKEN_USAGE_DIR = PHASE1_DIR / "token_usage"

EXPERIMENTS = {
    "llm_only": {
        "name": "LLM-only",
        "dir": ROOT / "LLM-only",
        "phase1_report": PHASE1_DIR / "phase1_llm_only.json",
    },
    "graphrag": {
        "name": "GraphRag",
        "dir": ROOT / "GraphRag",
        "phase1_report": PHASE1_DIR / "phase1_graphrag.json",
    },
    "kge": {
        "name": "KGE",
        "dir": ROOT / "KGE" / "KGE-based-graphrag",
        "phase1_report": PHASE1_DIR / "phase1_kge.json",
    },
    "kag": {
        "name": "KAG",
        "dir": ROOT / "KAG",
        "phase1_report": PHASE1_DIR / "phase1_kag.json",
    },
}


def run_command(cmd: list[str], cwd: Path) -> None:
    print(f"\n[{cwd.name}] $ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def compare_four_way(out_path: Path) -> None:
    cmd = [
        sys.executable,
        str(COMPARE_SCRIPT),
        "--out",
        str(out_path),
    ]
    run_command(cmd, ROOT)


def compare_token_usage(out_path: Path) -> None:
    cmd = [
        sys.executable,
        str(TOKEN_COMPARE_SCRIPT),
        "--out",
        str(out_path),
    ]
    run_command(cmd, ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run or re-evaluate LLM-only, GraphRag, KGE, and KAG experiments without reindexing or KGE retraining."
    )
    parser.add_argument(
        "--compare-dir",
        type=Path,
        default=Path("phase1"),
        help="Directory for phase1 comparison outputs (default: phase1)",
    )
    parser.add_argument(
        "--no-few-shot",
        action="store_true",
        help="Pass --no-few-shot to all nl_to_tio.py scripts",
    )
    parser.add_argument(
        "--eval-only",
        action="store_true",
        help="Skip nl_to_tio.py generation and only recompute phase1 evaluation and comparison outputs",
    )
    args = parser.parse_args()

    compare_dir = (ROOT / args.compare_dir).resolve()
    compare_dir.mkdir(parents=True, exist_ok=True)
    PHASE1_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_USAGE_DIR.mkdir(parents=True, exist_ok=True)

    for experiment_key, config in EXPERIMENTS.items():
        experiment_dir = config["dir"]
        nl_to_tio_cmd = [sys.executable, "nl_to_tio.py"]
        if args.no_few_shot:
            nl_to_tio_cmd.append("--no-few-shot")

        evaluate_cmd = [
            sys.executable,
            str(PHASE1_EVALUATOR),
            experiment_key,
        ]

        if not args.eval_only:
            run_command(nl_to_tio_cmd, experiment_dir)
        run_command(evaluate_cmd, ROOT)

    compare_path = OUTPUT_QUALITY_DIR / "compare_four_way.txt"
    compare_four_way(compare_path)
    token_compare_path = TOKEN_USAGE_DIR / "compare_token_usage.txt"
    compare_token_usage(token_compare_path)

    print("\nCompleted requested experiment workflow.")
    if args.eval_only:
        print("Generation step               : skipped (--eval-only)")
    else:
        print("Generation step               : executed")
    print(f"Phase1 outputs saved under    : {PHASE1_DIR}")
    print(f"Quality comparison saved to   : {compare_path}")
    print(f"Token comparison saved to     : {token_compare_path}")


if __name__ == "__main__":
    main()
