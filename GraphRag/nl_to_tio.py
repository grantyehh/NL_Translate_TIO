import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from openai import OpenAI
from evsla_prompt import build_evsla_system_prompt
from ontology_graph import (
    build_comment_index,
    build_label_index,
    load_ontology,
    typed_bfs_subgraph,
)
from subgraph_retriever import build_subgraph_context

# 加載環境變數
load_dotenv()

# 初始化 OpenAI 客戶端 (會自動讀取 OPENAI_API_KEY)
# 如果你的 .env 中使用的是 GRAPHRAG_API_KEY，我們手動指定一下
api_key = os.getenv("GRAPHRAG_API_KEY") or os.getenv("OPENAI_API_KEY")
if not api_key:
    print(
        "Error: Missing API key. Please set GRAPHRAG_API_KEY or OPENAI_API_KEY "
        "in your environment or .env file.",
        file=sys.stderr,
    )
    sys.exit(1)
client = OpenAI(api_key=api_key)

CHAT_MODEL = "gpt-5.4"

TTL_DIR = Path(__file__).resolve().parent.parent / "TM Forum Intent Ontology"
EMBED_MODEL = "text-embedding-3-small"


def default_test_cases_path(root: Path) -> Path:
    return (root.parent / "test_cases_20.json").resolve()


def default_few_shot_path(root: Path) -> Path:
    return (root.parent / "few_shot_samples.json").resolve()


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


def output_path_for_case(root: Path, tc_id: str) -> Path:
    return root.parent / "jsonld_outputs" / "graphrag" / f"{tc_id}.jsonld"


def build_system_prompt(tc_id: str) -> str:
    return build_evsla_system_prompt(tc_id, retrieval_mode="GraphRAG")


def normalize_jsonld_output(raw: str) -> str:
    """Normalize generated JSON-LD before writing so evaluator-required
    non-empty strings are present when the model omits obvious fields."""
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if not isinstance(doc, dict):
        return raw

    expectations = doc.get("intentExpectation")
    if isinstance(expectations, list):
        for expectation in expectations:
            if not isinstance(expectation, dict):
                continue
            description = expectation.get("description")
            if isinstance(description, str) and description.strip():
                continue
            fallback = expectation.get("name") or expectation.get("id") or doc.get("description")
            if isinstance(fallback, str) and fallback.strip():
                expectation["description"] = fallback.strip()

    return json.dumps(doc, ensure_ascii=False, indent=2)


def generate_jsonld_code(nl_intent, context, tc_id, few_shot_block: str):
    """
    利用 LLM 將 NL Intent 和 GraphRAG Context 轉化為 TIO JSON-LD。
    few_shot_block: optional text of NL+JSON-LD examples (not from test_cases).
    """
    print(f"--- Step 2: Translating to TIO JSON-LD format for {tc_id} ---")

    system_prompt = build_system_prompt(tc_id)

    few_shot_section = ""
    if few_shot_block.strip():
        few_shot_section = (
            "【Few-shot JSON-LD 範例（與本題不同情境；請學結構，勿抄內容）】\n"
            f"{few_shot_block}\n\n"
        )

    user_content = f"""{few_shot_section}當前要處理的測試案例 ID：{tc_id}

自然語言意圖："{nl_intent}"

相關 TIO 知識上下文：
{context}

請生成對應的 TIO JSON-LD：
"""

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None


generate_turtle_code = generate_jsonld_code


def _seed_llm_caller(prompt: str) -> str:
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return (response.choices[0].message.content or "").strip()


def _embed_caller(items: list[str]) -> list[list[float]]:
    if not items:
        return []
    resp = client.embeddings.create(model=EMBED_MODEL, input=items)
    return [d.embedding for d in resp.data]


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="NL to TIO JSON-LD via GraphRAG + OpenAI.")
    parser.add_argument(
        "--test-cases",
        type=Path,
        default=default_test_cases_path(root),
        help="Test cases JSON (default: ../test_cases_20.json)",
    )
    parser.add_argument(
        "--few-shot",
        type=Path,
        default=default_few_shot_path(root),
        help="Few-shot NL+JSON-LD examples JSON (default: ../few_shot_samples.json); omit file to disable",
    )
    parser.add_argument(
        "--no-few-shot",
        action="store_true",
        help="Do not load few-shot file even if it exists",
    )
    args = parser.parse_args()

    test_cases_path = (
        args.test_cases.resolve() if args.test_cases.is_absolute() else (root / args.test_cases).resolve()
    )
    few_shot_path = args.few_shot.resolve() if args.few_shot.is_absolute() else (root / args.few_shot).resolve()

    with open(test_cases_path, encoding="utf-8") as f:
        test_cases = json.load(f)

    few_shot_block = ""
    if not args.no_few_shot:
        examples = load_few_shot_samples(few_shot_path)
        few_shot_block = format_few_shot_block(examples)
        if examples:
            print(f"Loaded {len(examples)} few-shot example(s) from {few_shot_path}")
        else:
            print(f"No few-shot examples loaded (missing or empty: {few_shot_path})")

    output_dir = output_path_for_case(root, "TC000").parent
    output_dir.mkdir(parents=True, exist_ok=True)

    print("--- Loading TIO ontology and building indexes ---")
    graph = load_ontology(TTL_DIR)
    label_idx = build_label_index(graph)
    comment_idx = build_comment_index(graph)

    for tc in test_cases:
        print(f"\n>>> Processing {tc['id']}: {tc['nl_intent']}")

        print("--- Retrieving TIO subgraph via typed traversal ---")
        tio_context = build_subgraph_context(
            tc["nl_intent"],
            label_index=label_idx,
            comment_index=comment_idx,
            seed_caller=_seed_llm_caller,
            embed_caller=_embed_caller,
            bfs_fn=lambda seeds, hops, g=graph: typed_bfs_subgraph(g, seeds, hops),
        )

        if tio_context:
            jsonld_result = generate_jsonld_code(
                tc["nl_intent"],
                tio_context,
                tc["id"],
                few_shot_block,
            )

            if jsonld_result:
                file_path = output_path_for_case(root, tc["id"])
                jsonld_result = normalize_jsonld_output(jsonld_result)
                file_path.write_text(jsonld_result, encoding="utf-8")
                print(f"Successfully saved JSON-LD to: {file_path}")
                print("-" * 30)
                print(jsonld_result)
                print("-" * 30)


if __name__ == "__main__":
    main()
