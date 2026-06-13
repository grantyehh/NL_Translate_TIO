# Token Usage Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Phase 1 token usage evaluation with separate online and prep ledgers, plus amortized cost comparison at multiple workload sizes.

**Architecture:** Add a small root-level telemetry module that extracts provider usage, writes per-experiment JSON records, and aggregates ledgers. Add a token comparison script beside the existing quality comparator. Keep quality reports and token reports in separate `phase1/output_quality/` and `phase1/token_usage/` directories while preserving root-level quality report compatibility during migration.

**Tech Stack:** Python 3.11, `unittest`, OpenAI Python SDK response objects, JSON report files, existing Phase 1 runner scripts.

---

## File Structure

- Create `token_usage.py`: usage extraction, record creation, JSON persistence, aggregation, amortization.
- Create `compare_token_usage.py`: CLI that reads token telemetry and emits `phase1/token_usage/compare_token_usage.txt`.
- Create `tests/test_token_usage.py`: unit tests for extraction, aggregation, amortization, and missing-file behavior.
- Create `tests/test_compare_token_usage.py`: CLI and report formatting tests.
- Modify `evaluate_jsonld.py`: write quality reports to `phase1/output_quality/` and optionally mirror legacy root-level reports.
- Modify `compare_reports.py`: prefer `phase1/output_quality/` reports while falling back to legacy root-level reports.
- Modify `run_all_experiments.py`: create both Phase 1 subdirectories and run token comparison after generation/evaluation when telemetry exists.
- Modify `LLM-only/nl_to_tio.py`, `GraphRag/nl_to_tio.py`, `KGE/KGE-based-graphrag/nl_to_tio.py`, and `KAG/nl_to_tio.py`: record online token usage for directly visible API calls.
- Modify method tests as needed to assert telemetry stage names without external API calls.

## Task 1: Add Token Telemetry Core

**Files:**
- Create: `token_usage.py`
- Test: `tests/test_token_usage.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_token_usage.py` with tests for:

```python
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import token_usage


class TestTokenUsage(unittest.TestCase):
    def test_extract_chat_usage_accepts_openai_style_object(self):
        response = SimpleNamespace(
            usage=SimpleNamespace(
                prompt_tokens=11,
                completion_tokens=7,
                total_tokens=18,
            )
        )
        usage = token_usage.extract_usage(response)
        self.assertEqual(usage["input_tokens"], 11)
        self.assertEqual(usage["output_tokens"], 7)
        self.assertEqual(usage["total_tokens"], 18)
        self.assertEqual(usage["usage_source"], "response.usage")

    def test_extract_embedding_usage_has_zero_output_tokens(self):
        response = SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=13, total_tokens=13)
        )
        usage = token_usage.extract_usage(response)
        self.assertEqual(usage["input_tokens"], 13)
        self.assertEqual(usage["output_tokens"], 0)
        self.assertEqual(usage["total_tokens"], 13)

    def test_record_and_load_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "token_usage_llm_only.json"
            token_usage.record_usage(
                path,
                experiment="llm_only",
                ledger="online",
                case_id="TC001",
                stage="jsonld_generation",
                model="gpt-5.4",
                api="chat.completions",
                response=SimpleNamespace(
                    usage=SimpleNamespace(
                        prompt_tokens=10,
                        completion_tokens=5,
                        total_tokens=15,
                    )
                ),
            )
            rows = token_usage.load_usage_file(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["case_id"], "TC001")
            self.assertEqual(rows[0]["total_tokens"], 15)

    def test_aggregate_usage_separates_online_and_prep(self):
        rows = [
            {"ledger": "online", "case_id": "TC001", "input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            {"ledger": "online", "case_id": "TC002", "input_tokens": 20, "output_tokens": 10, "total_tokens": 30},
            {"ledger": "prep", "case_id": None, "input_tokens": 100, "output_tokens": 0, "total_tokens": 100},
        ]
        summary = token_usage.aggregate_usage(rows, amortize_over=[2, 10])
        self.assertEqual(summary["cases_processed"], 2)
        self.assertEqual(summary["prep_total_tokens"], 100)
        self.assertEqual(summary["total_online_tokens"], 45)
        self.assertEqual(summary["avg_online_total_tokens_per_case"], 22.5)
        self.assertEqual(summary["amortized_tokens_per_case"]["2"], 72.5)
        self.assertEqual(summary["amortized_tokens_per_case"]["10"], 32.5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m unittest tests.test_token_usage -v`

Expected: failure because `token_usage.py` does not exist.

- [ ] **Step 3: Implement `token_usage.py`**

Implement:

```python
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
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "usage_source": "missing"}
    input_tokens = int(_read_attr_or_key(usage, "prompt_tokens", _read_attr_or_key(usage, "input_tokens", 0)) or 0)
    output_tokens = int(_read_attr_or_key(usage, "completion_tokens", _read_attr_or_key(usage, "output_tokens", 0)) or 0)
    total_tokens = int(_read_attr_or_key(usage, "total_tokens", input_tokens + output_tokens) or 0)
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
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def reset_usage_file(path: Path) -> None:
    write_usage_file(path, [])


def record_usage(path: Path, *, experiment: str, ledger: str, case_id: str | None, stage: str, model: str, api: str, response: Any) -> dict[str, Any]:
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


def aggregate_usage(rows: list[dict[str, Any]], amortize_over: list[int] | None = None) -> dict[str, Any]:
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
```

- [ ] **Step 4: Run tests and verify pass**

Run: `python -m unittest tests.test_token_usage -v`

Expected: all tests pass.

## Task 2: Add Token Comparison CLI

**Files:**
- Create: `compare_token_usage.py`
- Test: `tests/test_compare_token_usage.py`

- [ ] **Step 1: Write failing tests**

Create tests that write temporary telemetry files, call `compare_token_usage.emit_report`, and assert that prep, online, and amortized columns appear.

- [ ] **Step 2: Implement comparator**

Create `compare_token_usage.py` with:

- `DEFAULT_REPORTS` pointing to `phase1/token_usage/token_usage_<experiment>.json`.
- `emit_report(reports, amortize_over)` that prints summary rows.
- CLI arg `--amortize-over`, default `20 100 1000`.
- CLI arg `--out`, default `phase1/token_usage/compare_token_usage.txt`.
- Missing telemetry files shown as `MISSING`, not zero.

- [ ] **Step 3: Run comparator tests**

Run: `python -m unittest tests.test_compare_token_usage -v`

Expected: all tests pass.

## Task 3: Move Quality Reports Into `phase1/output_quality`

**Files:**
- Modify: `evaluate_jsonld.py`
- Modify: `compare_reports.py`
- Test: `tests/test_evaluate_jsonld.py`
- Test: `tests/test_compare_reports.py`

- [ ] **Step 1: Write/update tests**

Assert that `evaluate_jsonld.phase1_dir()` or report path helpers target `phase1/output_quality`, and that `compare_reports.DEFAULT_REPORTS` prefers `phase1/output_quality/phase1_<experiment>.json`.

- [ ] **Step 2: Implement path changes**

Add:

```python
def output_quality_dir() -> Path:
    return ROOT / "phase1" / "output_quality"
```

Use it for new report paths. Keep legacy mirror writes if needed for compatibility.

- [ ] **Step 3: Run tests**

Run: `python -m unittest tests.test_evaluate_jsonld tests.test_compare_reports -v`

Expected: all tests pass.

## Task 4: Integrate Runner

**Files:**
- Modify: `run_all_experiments.py`
- Test: `tests/test_run_all_experiments.py`

- [ ] **Step 1: Update tests**

Assert `--help` still documents Phase 1 only, and add tests for exported constants:

- `OUTPUT_QUALITY_DIR == ROOT / "phase1" / "output_quality"`
- `TOKEN_USAGE_DIR == ROOT / "phase1" / "token_usage"`

- [ ] **Step 2: Implement runner updates**

Create both directories. Run quality comparison to `phase1/output_quality/compare_four_way.txt`. Run `compare_token_usage.py --out phase1/token_usage/compare_token_usage.txt` after generation/evaluation, but let missing telemetry be reported by the comparator.

- [ ] **Step 3: Run runner tests**

Run: `python -m unittest tests.test_run_all_experiments -v`

Expected: all tests pass.

## Task 5: Instrument Direct OpenAI Calls

**Files:**
- Modify: `LLM-only/nl_to_tio.py`
- Modify: `GraphRag/nl_to_tio.py`
- Modify: `KGE/KGE-based-graphrag/nl_to_tio.py`
- Modify: `KAG/nl_to_tio.py`
- Test: method-specific `test_nl_to_tio.py` files.

- [ ] **Step 1: Add usage path helpers**

Each method gets `token_usage_path()` returning the correct `phase1/token_usage/token_usage_<experiment>.json`.

- [ ] **Step 2: Reset telemetry at generation start**

Call `reset_usage_file(token_usage_path())` once at the start of `main()` unless the command is KAG `--resume`, where existing records should be preserved for skipped cases.

- [ ] **Step 3: Record direct API responses**

After each visible API response:

```python
record_usage(
    token_usage_path(),
    experiment="graphrag",
    ledger="online",
    case_id=tc_id,
    stage="jsonld_generation",
    model=CHAT_MODEL,
    api="chat.completions",
    response=response,
)
```

Use stages:

- `jsonld_generation`
- `seed_selection`
- `embedding`
- `kag_solver` for KAG visible wrapper records if available.

- [ ] **Step 4: Run method tests**

Run:

```bash
python -m unittest LLM-only/test_nl_to_tio.py GraphRag/test_nl_to_tio.py KGE/KGE-based-graphrag/test_nl_to_tio.py KAG/test_nl_to_tio.py -v
```

Expected: all tests pass.

## Task 6: Verify Full Local Test Suite

**Files:**
- No new files.

- [ ] **Step 1: Run focused tests**

Run:

```bash
python -m unittest tests.test_token_usage tests.test_compare_token_usage tests.test_evaluate_jsonld tests.test_compare_reports tests.test_run_all_experiments -v
```

Expected: all tests pass.

- [ ] **Step 2: Run method tests**

Run:

```bash
python -m unittest LLM-only/test_nl_to_tio.py GraphRag/test_nl_to_tio.py KGE/KGE-based-graphrag/test_nl_to_tio.py KAG/test_nl_to_tio.py -v
```

Expected: all tests pass without external API calls.

- [ ] **Step 3: Run eval-only smoke**

Run:

```bash
python run_all_experiments.py --eval-only
```

Expected: quality reports are written under `phase1/output_quality/`, token comparison is written under `phase1/token_usage/`, and missing telemetry is reported without crashing.

## Self-Review

Spec coverage:

- Online and prep ledgers are implemented by `token_usage.py`.
- Amortized cost at 20, 100, and 1000 is implemented by aggregation and comparator defaults.
- Separate `phase1/output_quality/` and `phase1/token_usage/` directories are implemented by path updates.
- Direct OpenAI calls are instrumented in the four method scripts.
- KAG internal provider-level instrumentation remains a known follow-up if KAG does not expose all internal calls through visible responses.

Placeholder scan:

- No `TBD`, `TODO`, or unresolved placeholders are intentionally left in this plan.

Type consistency:

- `input_tokens`, `output_tokens`, `total_tokens`, `ledger`, `case_id`, `stage`, `model`, `api`, and `usage_source` are used consistently across tests, core telemetry, and comparator.
