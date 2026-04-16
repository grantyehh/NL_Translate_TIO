#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

from compare_reports import aggregate_metrics, load_report


ROOT = Path(__file__).resolve().parent
COMPARE_SCRIPT = ROOT / "compare_reports.py"
PHASE1_EVALUATOR = ROOT / "evaluate_ttl.py"
PHASE1_DIR = ROOT / "phase1"
PHASE2_EVALUATOR = ROOT / "evaluate_ttl_phase2.py"
PHASE2_DIR = ROOT / "phase2"

EXPERIMENTS = {
    "llm_only": {
        "name": "LLM-only",
        "dir": ROOT / "LLM-only",
        "phase1_report": PHASE1_DIR / "phase1_llm_only.json",
        "phase2_report": PHASE2_DIR / "phase2_llm_only.json",
    },
    "graphrag": {
        "name": "GraphRag",
        "dir": ROOT / "GraphRag",
        "phase1_report": PHASE1_DIR / "phase1_graphrag.json",
        "phase2_report": PHASE2_DIR / "phase2_graphrag.json",
    },
    "kge_hybrid": {
        "name": "KGE-hybrid",
        "dir": ROOT / "KGE" / "KGE-based-graphrag",
        "phase1_report": PHASE1_DIR / "phase1_kge_hybrid.json",
        "phase2_report": PHASE2_DIR / "phase2_kge_hybrid.json",
    },
}


def run_command(cmd: list[str], cwd: Path) -> None:
    print(f"\n[{cwd.name}] $ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def render_three_way_summary(compare_dir: Path) -> Path:
    rows: list[tuple[str, dict]] = []
    for config in EXPERIMENTS.values():
        report_path = config["phase1_report"]
        metrics = aggregate_metrics(load_report(report_path))
        rows.append((config["name"], metrics))

    summary_path = PHASE1_DIR / "phase1_summary.txt"
    lines = [
        "Three-Way Summary",
        "-----------------",
        "",
        f"{'Experiment':14} | {'Cases':5} | {'Parse OK':10} | {'Avg coverage':12} | {'Avg triples':11} | {'Intent URI OK':13}",
        "-" * 82,
    ]
    for name, metrics in rows:
        lines.append(
            f"{name:14} | "
            f"{metrics['count']:5d} | "
            f"{metrics['parse_ok_rate'] * 100:9.2f}% | "
            f"{metrics['avg_coverage_ratio']:12.4f} | "
            f"{metrics['avg_triple_count']:11.2f} | "
            f"{metrics['intent_uri_ok_rate'] * 100:12.2f}%"
        )

    best_coverage = max(rows, key=lambda item: item[1]["avg_coverage_ratio"])
    fewest_triples = min(rows, key=lambda item: item[1]["avg_triple_count"])
    lines.extend(
        [
            "",
            f"Best average coverage : {best_coverage[0]} ({best_coverage[1]['avg_coverage_ratio']:.4f})",
            f"Fewest average triples: {fewest_triples[0]} ({fewest_triples[1]['avg_triple_count']:.2f})",
            "",
        ]
    )
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def render_phase2_summary(compare_dir: Path) -> Path:
    rows: list[tuple[str, list[dict]]] = []
    golden_ids = [f"TC{i:03d}" for i in range(1, 21)]
    for config in EXPERIMENTS.values():
        report_path = config["phase2_report"]
        with report_path.open("r", encoding="utf-8") as f:
            rows.append((config["name"], json.load(f)))

    by_name = {name: {row["case_id"]: row for row in report} for name, report in rows}
    summary_path = PHASE2_DIR / "phase2_summary.txt"
    lines = [
        "Phase-2 Summary",
        "---------------",
        "",
        f"{'Experiment':12} | {'Parse OK':8} | {'Golden cases':12} | {'must_have ok':12} | {'must_not ok':11} | {'expected_values ok':18} | {'avg structural':14}",
        "-" * 108,
    ]
    for name, report in rows:
        parse_ok = sum(1 for r in report if r["parse_ok"])
        g_rows = [by_name[name][cid] for cid in golden_ids]
        present = sum(1 for r in g_rows if r.get("golden_case_present"))
        mh = sum(1 for r in g_rows if (r.get("golden_evaluation") or {}).get("must_have_triples_ok"))
        mn = sum(1 for r in g_rows if (r.get("golden_evaluation") or {}).get("must_not_have_predicates_ok"))
        ev = sum(1 for r in g_rows if (r.get("golden_evaluation") or {}).get("expected_values_ok"))
        scores = [
            r["golden_evaluation"]["structural_score"]
            for r in g_rows
            if r.get("golden_evaluation") and r["golden_evaluation"].get("structural_score") is not None
        ]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        lines.append(
            f"{name:12} | {parse_ok:>6d}/20 | {present:>10d}/20 | {mh:>10d}/20 | {mn:>9d}/20 | {ev:>16d}/20 | {avg_score:14.4f}"
        )

    lines.extend(["", "Per-Golden-Case", "---------------", ""])
    for cid in golden_ids:
        lines.append(cid)
        for name, _ in rows:
            row = by_name[name][cid]
            ge = row.get("golden_evaluation") or {}
            lines.append(
                f"- {name}: parse_ok={row['parse_ok']}, coverage={row.get('expected_coverage_ratio')}, "
                f"must_have={ge.get('must_have_triples_ok')}, must_not={ge.get('must_not_have_predicates_ok')}, "
                f"expected_values={ge.get('expected_values_ok')}, structural_score={ge.get('structural_score')}"
            )
        lines.append("")

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def compare_pair(
    base_key: str,
    target_key: str,
    out_path: Path,
    test_cases_path: Path,
) -> None:
    base = EXPERIMENTS[base_key]
    target = EXPERIMENTS[target_key]
    cmd = [
        sys.executable,
        str(COMPARE_SCRIPT),
        "--base",
        str(base["phase1_report"]),
        "--target",
        str(target["phase1_report"]),
        "--base-name",
        base["name"],
        "--target-name",
        target["name"],
        "--test-cases",
        str(test_cases_path),
        "--out",
        str(out_path),
    ]
    run_command(cmd, ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run or re-evaluate LLM-only, GraphRag, and KGE-hybrid experiments without reindexing or KGE retraining."
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
        "--test-cases",
        type=Path,
        default=Path("test_cases_20.json"),
        help="Shared test cases JSON to pass to all experiment scripts and comparison steps (default: test_cases_20.json)",
    )
    parser.add_argument(
        "--phase",
        choices=("phase1", "phase2", "all"),
        default="phase1",
        help="Which evaluation phase to run after generation (default: phase1)",
    )
    parser.add_argument(
        "--eval-only",
        action="store_true",
        help="Skip nl_to_tio.py generation and only recompute the requested evaluation phase(s)",
    )
    args = parser.parse_args()

    compare_dir = (ROOT / args.compare_dir).resolve()
    compare_dir.mkdir(parents=True, exist_ok=True)
    PHASE1_DIR.mkdir(parents=True, exist_ok=True)
    PHASE2_DIR.mkdir(parents=True, exist_ok=True)
    test_cases_path = (ROOT / args.test_cases).resolve()

    for config in EXPERIMENTS.values():
        experiment_dir = config["dir"]
        nl_to_tio_cmd = [sys.executable, "nl_to_tio.py"]
        nl_to_tio_cmd.extend(["--test-cases", str(test_cases_path)])
        if args.no_few_shot:
            nl_to_tio_cmd.append("--no-few-shot")

        evaluate_cmd = [
            sys.executable,
            str(PHASE1_EVALUATOR),
            "--outputs-dir",
            str(experiment_dir / "tio_outputs"),
            "--json-out",
            str(config["phase1_report"]),
            "--test-cases",
            str(test_cases_path),
        ]

        if not args.eval_only:
            run_command(nl_to_tio_cmd, experiment_dir)
        if args.phase in {"phase1", "all"}:
            run_command(evaluate_cmd, ROOT)
        if args.phase in {"phase2", "all"}:
            phase2_cmd = [
                sys.executable,
                str(PHASE2_EVALUATOR),
                "--outputs-dir",
                str(experiment_dir / "tio_outputs"),
                "--test-cases",
                str(test_cases_path),
                "--json-out",
                str(config["phase2_report"]),
            ]
            run_command(phase2_cmd, ROOT)

    summary_paths: list[Path] = []
    if args.phase in {"phase1", "all"}:
        compare_pair("llm_only", "graphrag", compare_dir / "compare_llm_only_vs_graphrag.txt", test_cases_path)
        compare_pair("graphrag", "kge_hybrid", compare_dir / "compare_graphrag_vs_kge_hybrid.txt", test_cases_path)
        compare_pair("llm_only", "kge_hybrid", compare_dir / "compare_llm_only_vs_kge_hybrid.txt", test_cases_path)
        summary_paths.append(render_three_way_summary(compare_dir))
    if args.phase in {"phase2", "all"}:
        summary_paths.append(render_phase2_summary(compare_dir))

    print("\nCompleted requested experiment workflow.")
    if args.eval_only:
        print("Generation step               : skipped (--eval-only)")
    else:
        print("Generation step               : executed")
    if args.phase in {"phase1", "all"}:
        print(f"Phase1 outputs saved under    : {PHASE1_DIR}")
    if args.phase in {"phase2", "all"}:
        print(f"Phase2 outputs saved under    : {PHASE2_DIR}")
    for path in summary_paths:
        print(f"Summary saved to             : {path}")


if __name__ == "__main__":
    main()
