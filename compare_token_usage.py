#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import token_usage


ROOT = Path(__file__).resolve().parent
PHASE1_DIR = ROOT / "phase1"
TOKEN_USAGE_DIR = PHASE1_DIR / "token_usage"
DEFAULT_REPORTS = [
    ("LLM-only", TOKEN_USAGE_DIR / "token_usage_llm_only.json"),
    ("GraphRag", TOKEN_USAGE_DIR / "token_usage_graphrag.json"),
    ("KGE", TOKEN_USAGE_DIR / "token_usage_kge.json"),
    ("KAG", TOKEN_USAGE_DIR / "token_usage_kag.json"),
]


def print_header(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def emit_report(
    reports: list[tuple[str, Path]],
    amortize_over: list[int],
) -> None:
    print("Token Usage Reports")
    print("-------------------")
    for name, path in reports:
        print(f"{name:10}: {path}")

    print_header("Token Usage Summary")
    amortized_headers = " | ".join(f"{'Amortized @' + str(n):>15}" for n in amortize_over)
    print(
        f"{'Experiment':14} | {'Cases':5} | {'Prep total':12} | "
        f"{'Avg online':12} | {'Online total':12} | {'Avg calls':9} | {amortized_headers}"
    )
    print("-" * (75 + len(amortized_headers)))

    for name, path in reports:
        if not path.is_file():
            missing_values = " | ".join(f"{'MISSING':>15}" for _ in amortize_over)
            print(
                f"{name:14} | {'MISSING':>5} | {'MISSING':>12} | "
                f"{'MISSING':>12} | {'MISSING':>12} | {'MISSING':>9} | {missing_values}"
            )
            continue

        rows = token_usage.load_usage_file(path)
        summary = token_usage.aggregate_usage(rows, amortize_over=amortize_over)
        amortized_values = " | ".join(
            f"{summary['amortized_tokens_per_case'][str(n)]:15.2f}"
            for n in amortize_over
        )
        print(
            f"{name:14} | "
            f"{summary['cases_processed']:5d} | "
            f"{summary['prep_total_tokens']:12d} | "
            f"{summary['avg_online_total_tokens_per_case']:12.2f} | "
            f"{summary['total_online_tokens']:12d} | "
            f"{summary['avg_api_calls_per_case']:9.2f} | "
            f"{amortized_values}"
        )


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare Phase 1 token usage for LLM-only, GraphRag, KGE, and KAG."
    )
    parser.add_argument(
        "--amortize-over",
        nargs="+",
        type=int,
        default=[20, 100, 1000],
        help="Workload sizes used for prep-cost amortization (default: 20 100 1000)",
    )
    parser.add_argument(
        "--out",
        default=str(TOKEN_USAGE_DIR / "compare_token_usage.txt"),
        help="Output text report path (default: phase1/token_usage/compare_token_usage.txt)",
    )
    args = parser.parse_args(argv)

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    tee = Tee(sys.stdout, buffer)
    with redirect_stdout(tee):
        emit_report(DEFAULT_REPORTS, amortize_over=args.amortize_over)

    out_path.write_text(buffer.getvalue(), encoding="utf-8")
    print(f"\nSaved token usage comparison report to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
