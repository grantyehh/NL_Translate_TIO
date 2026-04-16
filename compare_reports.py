#!/usr/bin/env python3
import argparse
import io
import json
import sys
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, List, Tuple


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
        if not case_id:
            continue
        indexed[case_id] = row
    return indexed


def load_difficulty_map(path: Path) -> Dict[str, str]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Test cases file must be a JSON array: {path}")

    result: Dict[str, str] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        case_id = row.get("id")
        if not case_id:
            continue
        result[str(case_id)] = str(row.get("complexity", "N/A"))
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
    parse_ok = [bool(x.get("parse_ok")) for x in items]
    triple_count = [int(x.get("triple_count", 0)) for x in items]
    coverage = [coerce_float(x.get("expected_coverage_ratio", 0.0)) for x in items]
    intent_uri_ok = [bool(x.get("intent_uri_contains_case_id")) for x in items]
    return {
        "count": len(items),
        "parse_ok_rate": ratio_true(parse_ok),
        "avg_triple_count": mean(triple_count),
        "avg_coverage_ratio": mean(coverage),
        "intent_uri_ok_rate": ratio_true(intent_uri_ok),
    }


def collect_unknowns(items: List[dict], field: str) -> Counter:
    c = Counter()
    for row in items:
        for uri in row.get(field, []) or []:
            c[uri] += 1
    return c


def fmt_pct(v: float) -> str:
    return f"{v * 100:.2f}%"


def fmt_delta(v: float, percent: bool = False) -> str:
    if percent:
        return f"{v * 100:+.2f} pp"
    return f"{v:+.4f}"


def print_header(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def print_overall(base_metrics: dict, target_metrics: dict, base_name: str, target_name: str) -> None:
    print_header("Overall Summary")
    rows = [
        ("Cases", base_metrics["count"], target_metrics["count"], target_metrics["count"] - base_metrics["count"], False),
        (
            "Parse OK rate",
            fmt_pct(base_metrics["parse_ok_rate"]),
            fmt_pct(target_metrics["parse_ok_rate"]),
            target_metrics["parse_ok_rate"] - base_metrics["parse_ok_rate"],
            True,
        ),
        (
            "Avg coverage ratio",
            f"{base_metrics['avg_coverage_ratio']:.4f}",
            f"{target_metrics['avg_coverage_ratio']:.4f}",
            target_metrics["avg_coverage_ratio"] - base_metrics["avg_coverage_ratio"],
            False,
        ),
        (
            "Avg triple count",
            f"{base_metrics['avg_triple_count']:.2f}",
            f"{target_metrics['avg_triple_count']:.2f}",
            target_metrics["avg_triple_count"] - base_metrics["avg_triple_count"],
            False,
        ),
        (
            "Intent URI contains case_id",
            fmt_pct(base_metrics["intent_uri_ok_rate"]),
            fmt_pct(target_metrics["intent_uri_ok_rate"]),
            target_metrics["intent_uri_ok_rate"] - base_metrics["intent_uri_ok_rate"],
            True,
        ),
    ]

    print(f"{'Metric':36} | {base_name:14} | {target_name:14} | {'Delta(target-base)':17}")
    print("-" * 92)
    for metric, b, t, d, is_percent in rows:
        d_text = fmt_delta(d, percent=is_percent)
        print(f"{metric:36} | {str(b):14} | {str(t):14} | {d_text:17}")


def compare_cases(base_by_case: Dict[str, dict], target_by_case: Dict[str, dict], difficulty_map: Dict[str, str]) -> None:
    print_header("Per-Case Comparison")
    all_cases = sorted(set(base_by_case) | set(target_by_case))
    print(
        f"{'case_id':8} | {'base_cov':8} | {'target_cov':10} | {'delta_cov':9} | {'base_triples':12} | "
        f"{'target_triples':14} | {'delta_triples':12} | {'winner':8} | {'difficulty':10}"
    )
    print("-" * 122)
    for case_id in all_cases:
        b = base_by_case.get(case_id)
        t = target_by_case.get(case_id)
        difficulty = difficulty_map.get(case_id, "N/A")
        if not b or not t:
            side = "target_only" if t else "base_only"
            print(
                f"{case_id:8} | {'-':8} | {'-':10} | {'-':9} | {'-':12} | {'-':14} | {'-':12} | "
                f"{side:8} | {difficulty:10}"
            )
            continue

        b_cov = coerce_float(b.get("expected_coverage_ratio", 0.0))
        t_cov = coerce_float(t.get("expected_coverage_ratio", 0.0))
        d_cov = t_cov - b_cov
        b_tri = int(b.get("triple_count", 0))
        t_tri = int(t.get("triple_count", 0))
        d_tri = t_tri - b_tri

        if d_cov > 0:
            winner = "target"
        elif d_cov < 0:
            winner = "base"
        else:
            winner = "tie"

        print(
            f"{case_id:8} | {b_cov:8.4f} | {t_cov:10.4f} | {d_cov:+9.4f} | {b_tri:12d} | "
            f"{t_tri:14d} | {d_tri:+12d} | {winner:8} | {difficulty:10}"
        )


def print_unknown_diffs(base_items: List[dict], target_items: List[dict], field: str, top_n: int = 15) -> None:
    base_counter = collect_unknowns(base_items, field)
    target_counter = collect_unknowns(target_items, field)
    all_uris = set(base_counter) | set(target_counter)
    diffs: List[Tuple[str, int, int, int]] = []
    for uri in all_uris:
        b = base_counter.get(uri, 0)
        t = target_counter.get(uri, 0)
        diffs.append((uri, b, t, t - b))
    diffs.sort(key=lambda x: (abs(x[3]), x[0]), reverse=True)

    print_header(f"Top {top_n} Delta in {field}")
    print(f"{'delta':7} | {'base_count':10} | {'target_count':12} | uri")
    print("-" * 90)
    shown = 0
    for uri, b, t, d in diffs:
        if d == 0:
            continue
        print(f"{d:+7d} | {b:10d} | {t:12d} | {uri}")
        shown += 1
        if shown >= top_n:
            break
    if shown == 0:
        print("No difference.")


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


def emit_report(
    base_path: Path,
    target_path: Path,
    test_cases_path: Path,
    base_items: List[dict],
    target_items: List[dict],
    base_name: str,
    target_name: str,
    top_n: int,
) -> None:
    base_metrics = aggregate_metrics(base_items)
    target_metrics = aggregate_metrics(target_items)
    base_by_case = index_by_case(base_items)
    target_by_case = index_by_case(target_items)
    difficulty_map = load_difficulty_map(test_cases_path)

    print(f"Base report   : {base_path}")
    print(f"Target report : {target_path}")
    print(f"Test cases    : {test_cases_path}")

    print_overall(base_metrics, target_metrics, base_name, target_name)
    compare_cases(base_by_case, target_by_case, difficulty_map)
    print_unknown_diffs(base_items, target_items, "unknown_predicates", top_n=top_n)
    print_unknown_diffs(base_items, target_items, "unknown_types", top_n=top_n)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two GraphRAG evaluation reports (JSON arrays) and print terminal tables."
    )
    parser.add_argument("--base", required=True, help="Path to baseline report JSON (e.g., GraphRag/report.json)")
    parser.add_argument("--target", required=True, help="Path to target report JSON (e.g., report_kge.json)")
    parser.add_argument("--base-name", default="base", help="Display name for baseline report")
    parser.add_argument("--target-name", default="target", help="Display name for target report")
    parser.add_argument(
        "--test-cases",
        default="GraphRag/test_cases.json",
        help="Path to test cases JSON with id->complexity mapping",
    )
    parser.add_argument("--top-n", type=int, default=15, help="Top N rows for unknown deltas")
    parser.add_argument(
        "--out",
        default=None,
        help="If set, also write the comparison text report to this file",
    )
    args = parser.parse_args()

    base_path = Path(args.base).expanduser().resolve()
    target_path = Path(args.target).expanduser().resolve()
    test_cases_path = Path(args.test_cases).expanduser().resolve()
    base_items = load_report(base_path)
    target_items = load_report(target_path)
    out_path = Path(args.out).expanduser().resolve() if args.out else None

    if out_path is None:
        emit_report(
            base_path,
            target_path,
            test_cases_path,
            base_items,
            target_items,
            args.base_name,
            args.target_name,
            args.top_n,
        )
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    tee = Tee(sys.stdout, buffer)
    with redirect_stdout(tee):
        emit_report(
            base_path,
            target_path,
            test_cases_path,
            base_items,
            target_items,
            args.base_name,
            args.target_name,
            args.top_n,
        )

    out_path.write_text(buffer.getvalue(), encoding="utf-8")
    print(f"\nSaved comparison report to: {out_path}")


if __name__ == "__main__":
    main()
