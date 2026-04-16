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
        parts.append(
            f"--- Example {i} ({pat}) ---\n"
            f"Natural language:\n{ex.get('nl_intent', '')}\n\n"
            f"Turtle:\n{ex.get('turtle', '')}"
        )
    return "\n\n".join(parts)

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

def generate_turtle_code(
    nl_intent,
    context,
    tc_id,
    few_shot_block: str,
    kge_context: str | None = None,
):
    """
    利用 LLM 將 NL Intent 和 GraphRAG Context 轉化為 Turtle 代碼。
    """
    print(f"--- Step 2: Translating to TIO Turtle format for {tc_id} ---")
    
    system_prompt = f"""你是一位資深的電信意圖 (Intent) 專家，精通 TM Forum Intent Ontology (TIO) v3.6.0。
你的任務是將自然語言意圖轉換為符合 TIO 標準的 Turtle (RDF) 格式。

【命名空間 — 必須與官方 TIO Turtle 模組一致】
所有 TIO 詞彙（類別、屬性、函式等）必須使用下列 @prefix 所綁定的「官方 IRI」，字元級相同，不得改用其他 base、不得自創 namespace、不得把 icm:/imo:/fun: 指到 example.org 或 tmforum.org/ontologies 等非官方路徑：

@prefix icm:  <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix imo:  <http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/> .
@prefix fun:  <http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/> .
@prefix log:  <http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/> .
@prefix math: <http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions/> .
@prefix set:  <http://tio.models.tmforum.org/tio/v3.6.0/SetOperators/> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix t:    <http://www.w3.org/2006/time#> .

【實例 URI（個體／範例資源）】
僅「實例節點」（具名個體，如某筆 Intent、Expectation）可使用與詞彙不同的 base；請統一使用：
<http://example.org/tio-instance/{tc_id}/...>
其中 {tc_id} 為本次測試案例 ID，路徑須含該 ID 以便區分案例。勿將實例 URI 的 path 當成 TIO 類別或屬性名稱。

【Few-shot 使用方式】
若使用者訊息中提供 few-shot 範例，其情境與當前題目不同；請只學習前綴、CURIE 與圖結構，不要複製範例中的文字或個體內容。

【禁止事項】
- 禁止輸出 Markdown 或 code fence（例如 ```turtle）。
- 禁止在 Turtle 中使用非上列官方前綴來表達 TIO 已定義的類別與屬性（例如 http://example.org/icm#Intent、http://www.tmforum.org/ontologies/intent#... 皆不允許作為 TIO 詞彙）。
- 類別與屬性名稱須依 GraphRAG 上下文與 TIO 定義使用正確的 icm:/imo:/fun: 等 CURIE，且語意上應可對應官方本體中的術語。

【輸出格式】
僅輸出完整、可解析的 Turtle；第一行即可為 @prefix，不要任何前言或後記。"""

    kge_block = (kge_context or "").strip()
    if kge_block:
        kge_block = "\n\n" + kge_block + "\n"

    few_shot_section = ""
    if few_shot_block.strip():
        few_shot_section = (
            "【Few-shot 範例（與本題不同情境；請學結構，勿抄內容）】\n"
            f"{few_shot_block}\n\n"
        )

    user_content = f"""{few_shot_section}當前要處理的測試案例 ID：{tc_id}

自然語言意圖："{nl_intent}"

相關 TIO 知識上下文（GraphRAG 檢索）：
{context}
{kge_block}
請生成對應的 Turtle 代碼：
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
        turtle_code = response.choices[0].message.content.strip()
        return turtle_code
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="NL to TIO Turtle via GraphRAG + OpenAI + KGE.")
    parser.add_argument(
        "--test-cases",
        type=Path,
        default=Path("test_cases.json"),
        help="Test cases JSON (default: test_cases.json)",
    )
    parser.add_argument(
        "--few-shot",
        type=Path,
        default=Path("few_shot_samples.json"),
        help="Few-shot NL+Turtle examples JSON (default: few_shot_samples.json); omit file to disable",
    )
    parser.add_argument(
        "--no-few-shot",
        action="store_true",
        help="Do not load few-shot file even if it exists",
    )
    args = parser.parse_args()

    test_cases_path = (root / args.test_cases).resolve()
    few_shot_path = (root / args.few_shot).resolve()

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

    output_dir = root / "tio_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not kge_hybrid_ready():
        print(
            "--- KGE hybrid disabled: missing kge_data/ (run `pip install -r requirements.txt` "
            "then `python -m kge.train` with GRAPHRAG_API_KEY for full hybrid retrieval) ---"
        )

    # 處理 test_cases.json 中的全部案例
    for tc in test_cases:
        print(f"\n>>> Processing {tc['id']}: {tc['nl_intent']}")
        
        # 1. 檢索知識（要求回覆對齊官方詞彙，便於後續生成 Turtle）
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
            # 2. 生成 Turtle（GraphRAG + KGE 混合補強）
            turtle_result = generate_turtle_code(
                tc["nl_intent"],
                tio_context,
                tc["id"],
                few_shot_block,
                kge_context=kge_context or None,
            )
            
            if turtle_result:
                file_path = output_dir / f"{tc['id']}.ttl"
                file_path.write_text(turtle_result, encoding="utf-8")
                print(f"Successfully saved Turtle to: {file_path}")
                print("-" * 30)
                print(turtle_result)
                print("-" * 30)

if __name__ == "__main__":
    main()
