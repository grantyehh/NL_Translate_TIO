import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv
from openai import OpenAI
from evsla_prompt import build_evsla_system_prompt
from kge.retrieve import format_kge_context_for_prompt, kge_ready
from token_usage import record_usage, reset_usage_ledger

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

WEAK = False  # set True by --weak-prompt: weak system prompt + no few-shot + _weak outputs


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
        turtle = ex.get("turtle", "")
        parts.append(
            f"--- Example {i} ({pat}) ---\n"
            f"Natural language:\n{ex.get('nl_intent', '')}\n\n"
            f"Turtle:\n{turtle}"
        )
    return "\n\n".join(parts)


def output_path_for_case(root: Path, tc_id: str) -> Path:
    return root.parent.parent / "tio_outputs" / ("kge" + ("_weak" if WEAK else "")) / f"{tc_id}.ttl"


def token_usage_path(root: Path | None = None) -> Path:
    root = root or Path(__file__).resolve().parent
    return root.parent.parent / "phase1" / "token_usage" / f"token_usage_kge{'_weak' if WEAK else ''}.json"


def build_system_prompt(tc_id: str) -> str:
    return build_evsla_system_prompt(tc_id, retrieval_mode="KGE", weak_prompt=WEAK)

def generate_turtle_code(
    nl_intent,
    tc_id,
    few_shot_block: str,
    kge_context: str | None = None,
):
    """
    利用 LLM 將 NL Intent 和 KGE context 轉化為 TIO Turtle。
    """
    print(f"--- Translating to TIO Turtle format for {tc_id} ---")

    system_prompt = build_system_prompt(tc_id)

    kge_block = (kge_context or "").strip()
    if kge_block:
        kge_block = "\n\n" + kge_block + "\n"

    few_shot_section = ""
    if few_shot_block.strip():
        few_shot_section = (
            "【Few-shot Turtle 範例（與本題不同情境；請學結構，勿抄內容）】\n"
            f"{few_shot_block}\n\n"
        )

    user_content = f"""{few_shot_section}當前要處理的測試案例 ID：{tc_id}

自然語言意圖："{nl_intent}"

相關 TIO 知識上下文（KGE grounded URI / predicted likely triples）：
{kge_block}
請直接生成對應的 TIO Turtle。
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
        record_usage(
            token_usage_path(),
            experiment="kge" + ("_weak" if WEAK else ""),
            ledger="online",
            case_id=tc_id,
            stage="turtle_generation",
            model=CHAT_MODEL,
            api="chat.completions",
            response=response,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None


generate_jsonld_code = generate_turtle_code

def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="NL to TIO Turtle via KGE link prediction + OpenAI.")
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
        help="Few-shot NL+Turtle examples JSON (default: ../../few_shot_samples.json); omit file to disable",
    )
    parser.add_argument(
        "--no-few-shot",
        action="store_true",
        help="Do not load few-shot file even if it exists",
    )
    parser.add_argument(
        "--weak-prompt",
        action="store_true",
        help="Weak system prompt + no few-shot + _weak outputs",
    )
    args = parser.parse_args()

    global WEAK
    WEAK = args.weak_prompt
    if args.weak_prompt:
        args.no_few_shot = True

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
    reset_usage_ledger(token_usage_path(root), "online")

    if not kge_ready():
        print(
            "--- KGE context disabled: missing kge_data/ (run `pip install -r requirements.txt` "
            "then `python -m kge.train` with GRAPHRAG_API_KEY or OPENAI_API_KEY) ---"
        )

    # 處理 test_cases.json 中的全部案例
    for tc in test_cases:
        print(f"\n>>> Processing {tc['id']}: {tc['nl_intent']}")

        kge_context = format_kge_context_for_prompt(tc["nl_intent"], case_id=tc["id"])

        turtle_result = generate_turtle_code(
            tc["nl_intent"],
            tc["id"],
            few_shot_block,
            kge_context=kge_context or None,
        )

        if turtle_result:
            file_path = output_path_for_case(root, tc["id"])
            file_path.write_text(turtle_result, encoding="utf-8")
            print(f"Successfully saved Turtle to: {file_path}")
            print("-" * 30)
            print(turtle_result)
            print("-" * 30)

if __name__ == "__main__":
    main()
