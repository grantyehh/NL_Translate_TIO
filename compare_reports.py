#!/usr/bin/env python3
import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parent
PHASE1_DIR = ROOT / "phase1"
# evaluate_ttl.py writes the Turtle phase-1 reports here (phase1/phase1_<line>.json).
DEFAULT_REPORTS = [
    ("LLM-only", PHASE1_DIR / "phase1_llm_only.json"),
    ("GraphRag", PHASE1_DIR / "phase1_graphrag.json"),
    ("KGE", PHASE1_DIR / "phase1_kge.json"),
    ("KAG", PHASE1_DIR / "phase1_kag.json"),
]


def load_report(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Report must be a JSON array: {path}")
    return data


def index_by_case(items: List[dict]) -> Dict[str, dict]:
    indexed = {}
    for row in items:
        case_id = row.get("case_id")
        if case_id:
            indexed[str(case_id)] = row
    return indexed


def load_difficulty_map(path: Path) -> Dict[str, str]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Test cases file must be a JSON array: {path}")

    result: Dict[str, str] = {}
    for row in data:
        if isinstance(row, dict) and row.get("id"):
            result[str(row["id"])] = str(row.get("complexity", "N/A"))
    return result


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def ratio_true(values: List[bool]) -> float:
    return sum(1 for v in values if v) / len(values) if values else 0.0


def coerce_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def aggregate_metrics(items: List[dict]) -> dict:
    n = len(items)
    parse_ok = [bool(x.get("parse_ok")) for x in items]
    triple_count = [int(x.get("triple_count", 0) or 0) for x in items]
    coverage = [coerce_float(x.get("expected_coverage_ratio", 0.0)) for x in items]
    coverage_full = [c for c in coverage if c >= 0.999]
    intent_uri_ok = [bool(x.get("intent_uri_contains_case_id")) for x in items]
    fence_stripped = [bool(x.get("markdown_fence_stripped")) for x in items]
    unknown_predicate_total = sum(len(x.get("unknown_predicates") or []) for x in items)
    unknown_type_total = sum(len(x.get("unknown_types") or []) for x in items)
    return {
        "count": n,
        "parse_ok_rate": ratio_true(parse_ok),
        "avg_triple_count": mean(triple_count),
        "avg_coverage_ratio": mean(coverage),
        "coverage_full_rate": (len(coverage_full) / n if n else 0.0),
        "intent_uri_ok_rate": ratio_true(intent_uri_ok),
        "pure_turtle_rate": 1.0 - ratio_true(fence_stripped),
        "unknown_predicate_total": unknown_predicate_total,
        "unknown_type_total": unknown_type_total,
    }


def fmt_pct(v: float) -> str:
    return f"{v * 100:.2f}%"


def coverage(row: dict | None) -> float:
    return coerce_float((row or {}).get("expected_coverage_ratio", 0.0))


def triple_count(row: dict | None) -> int:
    return int((row or {}).get("triple_count", 0) or 0)


def print_header(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def print_overall(reports: list[tuple[str, Path, List[dict]]]) -> None:
    n = len(reports)
    label = {2: "Two-Way", 3: "Three-Way", 4: "Four-Way", 5: "Five-Way"}.get(n, f"{n}-Way")
    print_header(f"{label} Summary")
    print(
        f"{'Experiment':14} | {'Cases':5} | {'Parse OK':10} | {'Avg coverage':12} | "
        f"{'Cov=100%':10} | {'Avg triples':12} | {'Pure TTL':10} | "
        f"{'Unk pred':9} | {'Unk type':9} | {'Intent ID OK':12}"
    )
    print("-" * 134)
    rows: list[tuple[str, dict]] = []
    for name, _, items in reports:
        metrics = aggregate_metrics(items)
        rows.append((name, metrics))
        print(
            f"{name:14} | "
            f"{metrics['count']:5d} | "
            f"{metrics['parse_ok_rate'] * 100:9.2f}% | "
            f"{metrics['avg_coverage_ratio']:12.4f} | "
            f"{metrics['coverage_full_rate'] * 100:9.2f}% | "
            f"{metrics['avg_triple_count']:12.2f} | "
            f"{metrics['pure_turtle_rate'] * 100:9.2f}% | "
            f"{metrics['unknown_predicate_total']:9d} | "
            f"{metrics['unknown_type_total']:9d} | "
            f"{metrics['intent_uri_ok_rate'] * 100:12.2f}%"
        )

    best_coverage = max(rows, key=lambda item: item[1]["avg_coverage_ratio"])
    fewest_triples = min(rows, key=lambda item: item[1]["avg_triple_count"])
    cleanest = min(rows, key=lambda item: item[1]["unknown_predicate_total"] + item[1]["unknown_type_total"])
    print()
    print(
        f"Best average expected coverage  : {best_coverage[0]} "
        f"({best_coverage[1]['avg_coverage_ratio']:.4f})"
    )
    print(f"Fewest average triples          : {fewest_triples[0]} ({fewest_triples[1]['avg_triple_count']:.2f})")
    print(
        f"Cleanest vocabulary (unk pred+type): {cleanest[0]} "
        f"({cleanest[1]['unknown_predicate_total'] + cleanest[1]['unknown_type_total']})"
    )


def print_case_matrix(reports: list[tuple[str, Path, List[dict]]], difficulty_map: Dict[str, str]) -> None:
    n = len(reports)
    label = {2: "Two-Way", 3: "Three-Way", 4: "Four-Way", 5: "Five-Way"}.get(n, f"{n}-Way")
    print_header(f"Per-Case {label} Comparison")
    indexed = [(name, index_by_case(items)) for name, _, items in reports]
    all_cases = sorted(set().union(*(set(rows.keys()) for _, rows in indexed)))

    # 動態建表頭(每個 pipeline 取縮寫前 4 字元當欄位前綴)
    def short_label(s: str) -> str:
        return s.replace("-only", "").replace("-hybrid", "")[:8]

    cov_cols = " | ".join(f"{short_label(name)+' cov':>10}" for name, _, _ in reports)
    node_cols = " | ".join(f"{short_label(name)+' triples':>14}" for name, _, _ in reports)
    print(
        f"{'case_id':8} | {cov_cols} | {'winner':10} | {node_cols} | {'difficulty':10}"
    )
    print("-" * (24 + len(cov_cols) + len(node_cols)))
    for case_id in all_cases:
        rows = {name: by_case.get(case_id) for name, by_case in indexed}
        covs = {name: coverage(rows.get(name)) for name, _, _ in reports}
        best = max(covs.values())
        winners = [name for name, value in covs.items() if value == best]
        winner = "tie" if len(winners) > 1 else winners[0]
        cov_vals = " | ".join(f"{covs[name]:>10.4f}" for name, _, _ in reports)
        node_vals = " | ".join(f"{triple_count(rows.get(name)):>14d}" for name, _, _ in reports)
        print(
            f"{case_id:8} | {cov_vals} | "
            f"{winner:10} | {node_vals} | "
            f"{difficulty_map.get(case_id, 'N/A'):10}"
        )


def emit_report(reports: list[tuple[str, Path, List[dict]]], test_cases_path: Path) -> None:
    print("Reports")
    print("-------")
    for name, path, _ in reports:
        print(f"{name:10}: {path}")
    print(f"Test cases: {test_cases_path}")

    print_overall(reports)
    print_case_matrix(reports, load_difficulty_map(test_cases_path))


class Tee(io.TextIOBase):
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s: str) -> int:
        for stream in self.streams:
            stream.write(s)
        return len(s)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare phase1 reports for LLM-only, GraphRag, KGE, and KAG."
    )
    parser.add_argument(
        "--test-cases",
        default=None,
        help="Path to test cases JSON with id->complexity mapping (default: test_cases_20.json)",
    )
    parser.add_argument(
        "--out",
        default=str(PHASE1_DIR / "compare_four_way.txt"),
        help="Output text report path (default: phase1/compare_four_way.txt)",
    )
    args = parser.parse_args()

    test_cases_path = Path(args.test_cases).expanduser().resolve() if args.test_cases else ROOT / "test_cases_20.json"
    out_path = Path(args.out).expanduser().resolve() if args.out else None
    reports = [(name, path, load_report(path)) for name, path in DEFAULT_REPORTS]

    if out_path is None:
        emit_report(reports, test_cases_path)
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    tee = Tee(sys.stdout, buffer)
    with redirect_stdout(tee):
        emit_report(reports, test_cases_path)

    out_path.write_text(buffer.getvalue(), encoding="utf-8")
    print(f"\nSaved comparison report to: {out_path}")


if __name__ == "__main__":
    main()
