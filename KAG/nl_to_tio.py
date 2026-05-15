"""
NL → TIO JSON-LD via KAG retrieval(對齊 LLM-only / GraphRag / KGE 的 sibling contract)。

工作流:
  1. 對每筆 test case 的 nl_intent,呼叫 KAG kag_solver_pipeline_tc(static pipeline)
  2. KAG 跑 retrieval(5-way: atomic_query / outline / summary / vector / table)
     回吐相關 chunk 的原文
  3. 把 chunk 串成 context,丟給 LLM(系統 prompt 由 ../evsla_prompt.py 提供)
     + few-shot,生 JSON-LD
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
from openai import OpenAI
from evsla_prompt import build_evsla_system_prompt

load_dotenv()
API_KEY = os.getenv("GRAPHRAG_API_KEY") or os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("Error: Missing GRAPHRAG_API_KEY / OPENAI_API_KEY", file=sys.stderr)
    sys.exit(1)
CHAT_MODEL = os.getenv("GRAPHRAG_LLM_MODEL", "gpt-5.4")
openai_client = OpenAI(api_key=API_KEY)


# ─────────────────────────────────────────────────────────────────────
# Path helpers (相容於 run_all_experiments.py 與其他 pipeline)
# ─────────────────────────────────────────────────────────────────────

def default_test_cases_path() -> Path:
    return TIO_EXPERIMENT_ROOT / "test_cases_20.json"


def default_few_shot_path() -> Path:
    return TIO_EXPERIMENT_ROOT / "few_shot_samples.json"


def output_path_for_case(tc_id: str) -> Path:
    return TIO_EXPERIMENT_ROOT / "jsonld_outputs" / "kag" / f"{tc_id}.jsonld"


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


async def _kag_retrieve_async(query: str, verbose: bool = False) -> str:
    """呼叫 KAG static solver pipeline,回吐 retrieved chunks 串接的 context 字串。"""
    _ensure_kag_inited()

    from kag.common.conf import KAG_CONFIG
    from kag.interface import SolverPipelineABC

    try:
        # 用 _tc 版(static,單輪 retrieve)避免 iterative pipeline 多繞 LLM call
        pipeline = SolverPipelineABC.from_config(
            KAG_CONFIG.all_config["kag_solver_pipeline_tc"]
        )

        retrieved_chunks: list = []
        answer = None
        gen_failed = False
        try:
            answer = await pipeline.ainvoke(
                query,
                retrieved_chunks=retrieved_chunks,
            )
        except Exception as e:
            # 觀察到的情況:retriever 已把 chunks 填進 list,但 generator 階段對
            # gpt-5.4 的 JSON 輸出 parse 失敗。chunks 是有效的,繼續用。
            gen_failed = True
            print(f"  [KAG retrieve] generator step raised(chunks 仍可用): {e}",
                  file=sys.stderr)

        if verbose:
            tag = "(gen-failed)" if gen_failed else ""
            print(f"  [KAG retrieve] got {len(retrieved_chunks)} chunks {tag}",
                  file=sys.stderr)

        if not retrieved_chunks:
            return ""

        # 把 chunk content concat 成 context;每 chunk 之間用分隔線
        lines: list[str] = []
        for i, c in enumerate(retrieved_chunks, 1):
            content = getattr(c, "content", None) or str(c)
            title = getattr(c, "title", "") or ""
            score = getattr(c, "score", 0.0)
            header = f"--- Chunk {i}"
            if title:
                header += f" | {title}"
            header += f" | score={score:.3f} ---"
            lines.append(header)
            lines.append(content)
        return "\n".join(lines)
    except Exception as e:
        print(f"  [KAG retrieve] FAIL after pipeline init: {e}", file=sys.stderr)
        return ""


def query_kag(nl_intent: str, verbose: bool = False) -> str:
    """同步 wrapper(KAG pipeline 是 async)。"""
    print(f"--- Step 1: Querying KAG for TIO context ---")
    return asyncio.run(_kag_retrieve_async(nl_intent, verbose=verbose))


# ─────────────────────────────────────────────────────────────────────
# JSON-LD generation(對齊 GraphRag 的 context+few-shot 套路)
# ─────────────────────────────────────────────────────────────────────

def build_system_prompt(tc_id: str) -> str:
    return build_evsla_system_prompt(tc_id, retrieval_mode="KAG")


def generate_jsonld_code(
    nl_intent: str,
    context: str,
    tc_id: str,
    few_shot_block: str,
) -> str | None:
    print(f"--- Step 2: Translating to TIO JSON-LD format for {tc_id} ---")
    system_prompt = build_system_prompt(tc_id)

    few_shot_section = ""
    if few_shot_block.strip():
        few_shot_section = (
            "【Few-shot JSON-LD 範例(與本題不同情境;請學結構,勿抄內容)】\n"
            f"{few_shot_block}\n\n"
        )

    context_section = ""
    if context.strip():
        context_section = (
            "【KAG 檢索到的 TIO Ontology context】\n"
            f"{context}\n\n"
        )

    user_content = (
        f"{few_shot_section}"
        f"{context_section}"
        f"當前要處理的測試案例 ID:{tc_id}\n\n"
        f"自然語言意圖:\"{nl_intent}\"\n\n"
        f"請直接生成對應的 TIO JSON-LD。\n"
    )

    try:
        response = openai_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI API: {e}", file=sys.stderr)
        return None


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

    success = 0
    fail = 0
    for tc in test_cases:
        tc_id = tc["id"]
        nl = tc["nl_intent"]
        print(f"\n>>> Processing {tc_id}: {nl}")

        context = query_kag(nl, verbose=args.verbose)
        jsonld = generate_jsonld_code(nl, context, tc_id, few_shot_block)

        if jsonld:
            out = output_path_for_case(tc_id)
            out.write_text(jsonld, encoding="utf-8")
            print(f"Saved → {out}")
            if args.verbose:
                print("-" * 30)
                print(jsonld)
                print("-" * 30)
            success += 1
        else:
            fail += 1

    print(f"\nDone. success={success} fail={fail}")


if __name__ == "__main__":
    main()
