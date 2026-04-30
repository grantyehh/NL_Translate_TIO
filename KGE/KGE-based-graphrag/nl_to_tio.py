import argparse
import json
import os
import subprocess
import sys
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

from kge.retrieve import format_kge_context_for_prompt, kge_hybrid_ready

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


def default_test_cases_path(root: Path) -> Path:
    return (root.parent.parent / "test_cases_20.json").resolve()


def default_few_shot_path(root: Path) -> Path:
    return (root.parent.parent / "few_shot_samples.json").resolve()

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
    return root.parent.parent / "jsonld_outputs" / "kge_hybrid" / f"{tc_id}.jsonld"


def build_system_prompt(tc_id: str) -> str:
    return f"""你是一位資深的電信意圖 (Intent) 專家，精通 TM Forum Intent Ontology (TIO)、GraphRAG/KGE 檢索上下文與 JSON-LD API payload 設計。
你的任務是將自然語言意圖轉換為 API-friendly TIO JSON-LD，不是 Turtle。

【輸出目標】
輸出一個完整 JSON object，可被 json.loads 解析，並作為下游 intent API / compiler 的輸入。
不要輸出 Markdown、code fence、前言或後記。

【必要 top-level 欄位】
- "@context": 使用 "https://tmforum.org/schemas/intent-ontology/v1.jsonld"
- "@type": "Intent"
- "id": 使用可追蹤 ID，例如 "intent-{tc_id.lower()}"
- "name": 簡短英文名稱
- "description": 英文描述
- "intentOwner": 物件，至少包含 id 與 name；未知時使用 ops-manager-01 / Network Operations Center
- "intentExpectation": array，至少一個 expectation
- "intentContext": array；沒有明確 context 時可為 []
- "intentReport": 物件；沒有明確回報需求時使用 reportingInterval "PT5M" 與 handlerResponse "Continuous"

【Expectation 結構】
每個 intentExpectation 必須包含：
- "id", "name", "description"
- "@type": "DeliveryExpectation" 或 "PropertyExpectation"
- "expectationObject": 被意圖作用的 service / traffic class / resource，至少包含 id, name, "@type"
- "expectationTarget": array

【PropertyExpectation target 結構】
若是 latency、throughput、availability、bandwidth、priority 等屬性要求，expectationTarget 內每個 target 必須結構化表示：
- "name"
- "targetProperty": 例如 "latency", "throughput", "availability", "priority"
- "matchCondition": enum，例如 "LESS_THAN", "LESS_THAN_OR_EQUAL", "GREATER_THAN", "GREATER_THAN_OR_EQUAL", "EQUALS"
- "targetValue": 物件，數值型門檻使用 {{ "value": number, "unit": string }}

【GraphRAG / KGE 使用方式】
- GraphRAG 與 KGE 上下文用來協助選擇 intent 類型、目標資源、metric 與條件，但最終輸出仍必須是 JSON-LD。
- 若檢索上下文提供可用 service/resource id，優先放入 expectationObject.id。
- 不要把檢索文字整段塞進 description；只抽取必要結構。

【建模原則】
- 核心語意必須放在 JSON 欄位，不可只寫在 description。
- 若自然語言中有多個核心 requirement，拆成多個 intentExpectation。
- 若有地點、時間、事件條件，放入 intentContext。
"""

def query_graphrag_local(query_text):
    """
    呼叫 GraphRAG 的 local search 獲取 TIO 相關的 Schema 上下文。
    """
    print(f"--- Step 1: Querying GraphRAG for TIO context ---")
    try:
        result = subprocess.run(
            ["graphrag", "query", "--root", ".", "--method", "local", query_text],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error querying GraphRAG: {e.stderr}")
        return None

def generate_jsonld_code(
    nl_intent,
    context,
    tc_id,
    few_shot_block: str,
    kge_context: str | None = None,
):
    """
    利用 LLM 將 NL Intent 和 GraphRAG/KGE Context 轉化為 TIO JSON-LD。
    """
    print(f"--- Step 2: Translating to TIO JSON-LD format for {tc_id} ---")
    
    system_prompt = build_system_prompt(tc_id)

    kge_block = (kge_context or "").strip()
    if kge_block:
        kge_block = "\n\n" + kge_block + "\n"

    few_shot_section = ""
    if few_shot_block.strip():
        few_shot_section = (
            "【Few-shot JSON-LD 範例（與本題不同情境；請學結構，勿抄內容）】\n"
            f"{few_shot_block}\n\n"
        )

    user_content = f"""{few_shot_section}當前要處理的測試案例 ID：{tc_id}

自然語言意圖："{nl_intent}"

相關 TIO 知識上下文（GraphRAG 檢索）：
{context}
{kge_block}
請生成對應的 TIO JSON-LD：
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
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

def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="NL to TIO JSON-LD via GraphRAG + OpenAI + KGE.")
    parser.add_argument(
        "--test-cases",
        type=Path,
        default=default_test_cases_path(root),
        help="Test cases JSON (default: ../../test_cases_20.json)",
    )
    parser.add_argument(
        "--few-shot",
        type=Path,
        default=default_few_shot_path(root),
        help="Few-shot NL+JSON-LD examples JSON (default: ../../few_shot_samples.json); omit file to disable",
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

    if not kge_hybrid_ready():
        print(
            "--- KGE hybrid disabled: missing kge_data/ (run `pip install -r requirements.txt` "
            "then `python -m kge.train` with GRAPHRAG_API_KEY for full hybrid retrieval) ---"
        )

    # 處理 test_cases.json 中的全部案例
    for tc in test_cases:
        print(f"\n>>> Processing {tc['id']}: {tc['nl_intent']}")
        
        # 1. 檢索知識（要求回覆對齊官方詞彙，便於後續生成 JSON-LD）
        query_text = (
            f"請根據 TM Forum Intent Ontology (TIO) v3.6.0，說明如何表達下列自然語言意圖：「{tc['nl_intent']}」。\n"
            "請務必使用與官方本體一致的術語：\n"
            "- 以 CURIE 形式寫出相關類別與屬性（例如 icm:Intent、icm:DeliveryExpectation、icm:target），"
            "命名空間須為 http://tio.models.tmforum.org/tio/v3.6.0/ 底下各模組。\n"
            "- 屬性與類別請使用本體文件中實際的 local name（例如 icm:target），"
            "不要自行發明 Java 風格的 hasX 名稱，除非本體中確實定義該名稱。\n"
            "- 簡要說明各術語在意圖中的角色，以及建議的個體／關聯方向。"
        )
        tio_context = query_graphrag_local(query_text)

        kge_context = format_kge_context_for_prompt(tc["nl_intent"])

        if tio_context:
            # 2. 生成 JSON-LD（GraphRAG + KGE 混合補強）
            jsonld_result = generate_jsonld_code(
                tc["nl_intent"],
                tio_context,
                tc["id"],
                few_shot_block,
                kge_context=kge_context or None,
            )
            
            if jsonld_result:
                file_path = output_path_for_case(root, tc["id"])
                file_path.write_text(jsonld_result, encoding="utf-8")
                print(f"Successfully saved JSON-LD to: {file_path}")
                print("-" * 30)
                print(jsonld_result)
                print("-" * 30)

if __name__ == "__main__":
    main()
