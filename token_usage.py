from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_attr_or_key(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def extract_usage(response: Any) -> dict[str, Any]:
    usage = _read_attr_or_key(response, "usage")
    if usage is None:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "usage_source": "missing",
        }

    input_tokens = int(
        _read_attr_or_key(
            usage,
            "prompt_tokens",
            _read_attr_or_key(usage, "input_tokens", 0),
        )
        or 0
    )
    output_tokens = int(
        _read_attr_or_key(
            usage,
            "completion_tokens",
            _read_attr_or_key(usage, "output_tokens", 0),
        )
        or 0
    )
    total_tokens = int(
        _read_attr_or_key(usage, "total_tokens", input_tokens + output_tokens)
        or 0
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "usage_source": "response.usage",
    }


def load_usage_file(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Token usage file must contain a JSON array: {path}")
    return [row for row in data if isinstance(row, dict)]


def write_usage_file(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def reset_usage_file(path: Path) -> None:
    write_usage_file(path, [])


def record_usage(
    path: Path,
    *,
    experiment: str,
    ledger: str,
    case_id: str | None,
    stage: str,
    model: str,
    api: str,
    response: Any,
) -> dict[str, Any]:
    usage = extract_usage(response)
    record = {
        "experiment": experiment,
        "ledger": ledger,
        "case_id": case_id,
        "stage": stage,
        "model": model,
        "api": api,
        **usage,
    }
    rows = load_usage_file(path)
    rows.append(record)
    write_usage_file(path, rows)
    return record


def record_usage_counts(
    path: Path,
    *,
    experiment: str,
    ledger: str,
    case_id: str | None,
    stage: str,
    model: str,
    api: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    usage_source: str,
) -> dict[str, Any]:
    record = {
        "experiment": experiment,
        "ledger": ledger,
        "case_id": case_id,
        "stage": stage,
        "model": model,
        "api": api,
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "total_tokens": int(total_tokens or 0),
        "usage_source": usage_source,
    }
    rows = load_usage_file(path)
    rows.append(record)
    write_usage_file(path, rows)
    return record


def reset_usage_ledger(path: Path, ledger: str) -> None:
    rows = [row for row in load_usage_file(path) if row.get("ledger") != ledger]
    write_usage_file(path, rows)


def aggregate_usage(
    rows: list[dict[str, Any]],
    amortize_over: list[int] | None = None,
) -> dict[str, Any]:
    amortize_over = amortize_over or [20, 100, 1000]
    online = [row for row in rows if row.get("ledger") == "online"]
    prep = [row for row in rows if row.get("ledger") == "prep"]
    cases = sorted({str(row.get("case_id")) for row in online if row.get("case_id")})
    case_count = len(cases)

    online_input = sum(int(row.get("input_tokens", 0) or 0) for row in online)
    online_output = sum(int(row.get("output_tokens", 0) or 0) for row in online)
    online_total = sum(int(row.get("total_tokens", 0) or 0) for row in online)
    prep_input = sum(int(row.get("input_tokens", 0) or 0) for row in prep)
    prep_output = sum(int(row.get("output_tokens", 0) or 0) for row in prep)
    prep_total = sum(int(row.get("total_tokens", 0) or 0) for row in prep)
    avg_online_total = online_total / case_count if case_count else 0.0

    return {
        "cases_processed": case_count,
        "prep_input_tokens": prep_input,
        "prep_output_tokens": prep_output,
        "prep_total_tokens": prep_total,
        "avg_online_input_tokens_per_case": online_input / case_count if case_count else 0.0,
        "avg_online_output_tokens_per_case": online_output / case_count if case_count else 0.0,
        "avg_online_total_tokens_per_case": avg_online_total,
        "total_online_tokens": online_total,
        "avg_api_calls_per_case": len(online) / case_count if case_count else 0.0,
        "amortized_tokens_per_case": {
            str(n): avg_online_total + (prep_total / n if n else 0.0)
            for n in amortize_over
        },
    }
