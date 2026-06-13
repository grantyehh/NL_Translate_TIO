"""
NL → TIO JSON-LD via native KAG solver flow(對齊 LLM-only / GraphRag / KGE 的 sibling contract)。

工作流:
  1. 對每筆 test case 的 nl_intent,呼叫 KAG kag_solver_pipeline_tc(static pipeline)
  2. KAG solver 做 planning → retrieval / reasoning executor
  3. KAG solver 的 generator 階段使用 TIO JSON-LD prompt 產生 final JSON-LD
  4. 寫到 ../jsonld_outputs/kag/<TCID>.jsonld

前置條件:
  - docker stack up(`docker compose -f docker-compose-west.yml up -d`)
  - KAG venv 啟用(`source .venv/bin/activate`)
  - kag_config.yaml 已 render(`example_project/render_config.sh`)
  - KG 已灌(`python example_project/builder/indexer.py`)
  - GRAPHRAG_API_KEY in env

用法:
  python nl_to_tio.py                  # 全 20 題
  python nl_to_tio.py --limit 1        # 只跑前 1 題(試水)
  python nl_to_tio.py --case TC001     # 跑指定 case
  python nl_to_tio.py --from-case TC014 # 從指定 case 往後跑(會覆蓋既有輸出)
  python nl_to_tio.py --resume         # 跳過已產生的 output,從中斷點續跑
  python nl_to_tio.py --no-few-shot    # 不帶 few-shot
  python nl_to_tio.py --verbose        # 印出 KAG retrieved chunks(debug)
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# 加 parent 進 path 讓 evsla_prompt 可 import(同 LLM-only / GraphRag 的 pattern)
ROOT_KAG = Path(__file__).resolve().parent
TIO_EXPERIMENT_ROOT = ROOT_KAG.parent
sys.path.insert(0, str(TIO_EXPERIMENT_ROOT))

from dotenv import load_dotenv
from token_usage import record_usage_counts, reset_usage_ledger

load_dotenv()
API_KEY = os.getenv("GRAPHRAG_API_KEY") or os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("Error: Missing GRAPHRAG_API_KEY / OPENAI_API_KEY", file=sys.stderr)
    sys.exit(1)
CHAT_MODEL = os.getenv("GRAPHRAG_LLM_MODEL", "gpt-5.4")


# ─────────────────────────────────────────────────────────────────────
# Path helpers (相容於 run_all_experiments.py 與其他 pipeline)
# ─────────────────────────────────────────────────────────────────────

def default_test_cases_path() -> Path:
    return TIO_EXPERIMENT_ROOT / "test_cases_20.json"


def default_few_shot_path() -> Path:
    return TIO_EXPERIMENT_ROOT / "few_shot_samples.json"


def output_path_for_case(tc_id: str) -> Path:
    return TIO_EXPERIMENT_ROOT / "jsonld_outputs" / "kag" / f"{tc_id}.jsonld"


def token_usage_path() -> Path:
    return TIO_EXPERIMENT_ROOT / "phase1" / "token_usage" / "token_usage_kag.json"


def example_project_dir() -> Path:
    return ROOT_KAG / "example_project"


# ─────────────────────────────────────────────────────────────────────
# Few-shot loading(逐字對齊 LLM-only / GraphRag 的格式)
# ─────────────────────────────────────────────────────────────────────

def load_few_shot_samples(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("examples") or [])


def format_few_shot_block(examples: list[dict]) -> str:
    if not examples:
        return ""
    parts: list[str] = []
    for i, ex in enumerate(examples, 1):
        pat = ex.get("pattern", "")
        jsonld = ex.get("jsonld", {})
        if not isinstance(jsonld, str):
            jsonld = json.dumps(jsonld, ensure_ascii=False, indent=2)
        parts.append(
            f"--- Example {i} ({pat}) ---\n"
            f"Natural language:\n{ex.get('nl_intent', '')}\n\n"
            f"JSON-LD:\n{jsonld}"
        )
    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────
# KAG retrieval — chdir 到 example_project/ 讓 KAG 找得到 kag_config.yaml
# ─────────────────────────────────────────────────────────────────────

_kag_inited = False


def _ensure_kag_inited() -> None:
    """`kag/__init__.py` 自動跑的 init_env() 從 CWD 找 kag_config.yaml,
    但我們從 KAG/ 跑時 CWD 沒這檔。手動 init_env() 指向 example_project/kag_config.yaml。"""
    global _kag_inited
    if _kag_inited:
        return
    from kag.common.conf import init_env
    from kag.common.registry import import_modules_from_path

    cfg = example_project_dir() / "kag_config.yaml"
    if not cfg.is_file():
        raise FileNotFoundError(
            f"kag_config.yaml not found at {cfg}. "
            f"Run example_project/render_config.sh first."
        )
    init_env(config_file=str(cfg))
    import_modules_from_path(str(example_project_dir()))
    _kag_inited = True


async def _kag_solve_async(
    query: str,
    tc_id: str,
    few_shot_block: str,
    verbose: bool = False,
) -> str:
    """呼叫 KAG static solver pipeline,回吐 KAG generator 產生的 final JSON-LD。"""
    _ensure_kag_inited()

    from kag.common.conf import KAG_CONFIG
    from kag.interface import SolverPipelineABC
    from kag.interface.common.llm_client import LLMCallCcontext, TokenMeterFactory
    from kag.interface import LLMClient

    try:
        # 用 _tc 版(static,單輪 planning/execution/generation)避免 iterative pipeline 多繞 LLM call。
        pipeline = SolverPipelineABC.from_config(
            KAG_CONFIG.all_config["kag_solver_pipeline_tc"]
        )
        task_id = f"kag-online-{tc_id}"
        TokenMeterFactory().clear_all()
        with LLMCallCcontext(task_id, True):
            answer = await pipeline.ainvoke(
                query,
                tc_id=tc_id,
                few_shot_block=few_shot_block,
            )
            stat = LLMClient.get_token_meter().to_dict()
        record_usage_counts(
            token_usage_path(),
            experiment="kag",
            ledger="online",
            case_id=tc_id,
            stage="kag_solver",
            model=CHAT_MODEL,
            api="kag.llm_meter",
            input_tokens=stat.get("prompt_tokens", 0),
            output_tokens=stat.get("completion_tokens", 0),
            total_tokens=stat.get("total_tokens", 0),
            usage_source="kag.LLMClient.TokenMeter",
        )
        if verbose:
            print("  [KAG solver] final answer generated by KAG generator", file=sys.stderr)
        return str(answer or "").strip()
    except Exception as e:
        print(f"  [KAG solver] FAIL after pipeline init: {e}", file=sys.stderr)
        return ""


def query_kag(
    nl_intent: str,
    tc_id: str,
    few_shot_block: str,
    verbose: bool = False,
) -> str:
    """同步 wrapper(KAG pipeline 是 async)。"""
    print("--- Step 1: Solving with native KAG pipeline ---")
    return asyncio.run(
        _kag_solve_async(
            nl_intent,
            tc_id=tc_id,
            few_shot_block=few_shot_block,
            verbose=verbose,
        )
    )


# ─────────────────────────────────────────────────────────────────────
# JSON-LD generation(對齊 GraphRag 的 context+few-shot 套路)
# ─────────────────────────────────────────────────────────────────────

def generate_jsonld_code(
    nl_intent: str,
    tc_id: str,
    few_shot_block: str,
    verbose: bool = False,
) -> str | None:
    print(f"--- Step 2: Generating TIO JSON-LD inside KAG solver for {tc_id} ---")
    return query_kag(
        nl_intent,
        tc_id=tc_id,
        few_shot_block=few_shot_block,
        verbose=verbose,
    )


def ensure_jsonld_contract(jsonld: str) -> str:
    """Fill deterministic output-contract fields the KAG generator may omit."""
    try:
        data = json.loads(jsonld)
    except json.JSONDecodeError:
        return jsonld
    if not isinstance(data, dict):
        return jsonld

    if not isinstance(data.get("intentReport"), dict):
        data["intentReport"] = {
            "reportingInterval": "PT5M",
            "handlerResponse": "Continuous",
        }

    return json.dumps(data, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="NL to TIO JSON-LD via KAG retrieval.")
    parser.add_argument("--test-cases", type=Path, default=default_test_cases_path())
    parser.add_argument("--few-shot", type=Path, default=default_few_shot_path())
    parser.add_argument("--no-few-shot", action="store_true")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only process first N test cases (for試水)")
    parser.add_argument("--case", type=str, default=None,
                        help="Only process this single TCxxx id")
    parser.add_argument("--from-case", type=str, default=None,
                        help="Process from this TCxxx id onward")
    parser.add_argument("--resume", action="store_true",
                        help="Skip cases whose output JSON-LD already exists")
    parser.add_argument("--verbose", action="store_true",
                        help="Print KAG retrieval debug info")
    args = parser.parse_args()

    with open(args.test_cases, encoding="utf-8") as f:
        test_cases = json.load(f)

    if args.case:
        test_cases = [tc for tc in test_cases if tc.get("id") == args.case]
        if not test_cases:
            print(f"Error: no test case with id={args.case}", file=sys.stderr)
            sys.exit(1)

    if args.from_case:
        start_idx = next(
            (i for i, tc in enumerate(test_cases) if tc.get("id") == args.from_case),
            None,
        )
        if start_idx is None:
            print(f"Error: no test case with id={args.from_case}", file=sys.stderr)
            sys.exit(1)
        test_cases = test_cases[start_idx:]

    if args.limit is not None:
        test_cases = test_cases[: args.limit]

    few_shot_block = ""
    if not args.no_few_shot:
        examples = load_few_shot_samples(args.few_shot)
        few_shot_block = format_few_shot_block(examples)
        if examples:
            print(f"Loaded {len(examples)} few-shot example(s) from {args.few_shot}")

    output_dir = output_path_for_case("TC000").parent
    output_dir.mkdir(parents=True, exist_ok=True)
    if not args.resume:
        reset_usage_ledger(token_usage_path(), "online")

    success = 0
    skipped = 0
    fail = 0
    for tc in test_cases:
        tc_id = tc["id"]
        nl = tc["nl_intent"]
        out = output_path_for_case(tc_id)

        if args.resume and out.is_file() and out.stat().st_size > 0:
            print(f"\n>>> Skipping {tc_id}: existing output at {out}")
            skipped += 1
            continue

        print(f"\n>>> Processing {tc_id}: {nl}")

        jsonld = generate_jsonld_code(
            nl,
            tc_id,
            few_shot_block,
            verbose=args.verbose,
        )

        if jsonld:
            jsonld = ensure_jsonld_contract(jsonld)
            out.write_text(jsonld, encoding="utf-8")
            print(f"Saved → {out}")
            if args.verbose:
                print("-" * 30)
                print(jsonld)
                print("-" * 30)
            success += 1
        else:
            fail += 1

    print(f"\nDone. success={success} skipped={skipped} fail={fail}")


if __name__ == "__main__":
    main()
