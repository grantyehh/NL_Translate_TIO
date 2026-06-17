import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from evsla_prompt import build_evsla_system_prompt
from kge.retrieve import kge_ready
from kge.select import build_kge_context
from openai_config import chat_model, create_client, load_project_env
from token_usage import record_usage, reset_usage_ledger

CHAT_MODEL = "gpt-5.4"

WEAK = False  # legacy flag: True maps to PROFILE="weak"
PROFILE = "strong"  # choices: "strong", "weak", "structure_only"

# Populated in main(); exposed at module level so tests can patch it.
client = None


def _experiment_key() -> str:
    if PROFILE == "structure_only":
        return "kge_structure"
    if PROFILE == "weak":
        return "kge_weak"
    return "kge"


def default_test_cases_path(root: Path) -> Path:
    return (root.parent.parent / "test_cases_20.json").resolve()


def default_few_shot_path(root: Path) -> Path:
    return (root.parent.parent / "few_shot_samples.json").resolve()


def default_structure_only_few_shot_path(root: Path) -> Path:
    return (root.parent.parent / "few_shot_structure_only.json").resolve()


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
    return root.parent.parent / "tio_outputs" / _experiment_key() / f"{tc_id}.ttl"


def token_usage_path(root: Path | None = None) -> Path:
    root = root or Path(__file__).resolve().parent
    return root.parent.parent / "phase1" / "token_usage" / f"token_usage_{_experiment_key()}.json"


def build_context_for_case(nl_intent: str, tc_id: str, root: Path) -> str:
    """Build KGE context while routing retrieval token usage to this profile's ledger."""
    old_experiment = os.environ.get("KGE_TOKEN_USAGE_EXPERIMENT")
    old_path = os.environ.get("KGE_TOKEN_USAGE_PATH")
    os.environ["KGE_TOKEN_USAGE_EXPERIMENT"] = _experiment_key()
    os.environ["KGE_TOKEN_USAGE_PATH"] = str(token_usage_path(root))
    try:
        return build_kge_context(nl_intent, case_id=tc_id)
    finally:
        if old_experiment is None:
            os.environ.pop("KGE_TOKEN_USAGE_EXPERIMENT", None)
        else:
            os.environ["KGE_TOKEN_USAGE_EXPERIMENT"] = old_experiment
        if old_path is None:
            os.environ.pop("KGE_TOKEN_USAGE_PATH", None)
        else:
            os.environ["KGE_TOKEN_USAGE_PATH"] = old_path


def build_system_prompt(tc_id: str) -> str:
    return build_evsla_system_prompt(tc_id, retrieval_mode="KGE", profile=PROFILE)

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
        model = chat_model(CHAT_MODEL)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
        )
        record_usage(
            token_usage_path(),
            experiment=_experiment_key(),
            ledger="online",
            case_id=tc_id,
            stage="turtle_generation",
            model=model,
            api="chat.completions",
            response=response,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None


def ensure_complete_generation(written: int, total: int, output_dir: Path) -> None:
    if written != total:
        raise SystemExit(
            f"Generated {written}/{total} TTL files in {output_dir}. "
            "Aborting evaluation to avoid mixing stale outputs with a failed run."
        )


generate_jsonld_code = generate_turtle_code

def main() -> None:
    global WEAK, PROFILE, client

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
        help="Weak system prompt + no few-shot + _weak outputs (maps to --prompt-profile weak)",
    )
    parser.add_argument(
        "--prompt-profile",
        choices=["strong", "weak", "structure_only"],
        default="strong",
        help="Prompt profile: strong (default), weak, or structure_only",
    )
    args = parser.parse_args()

    # --weak-prompt is legacy; it maps to profile="weak"
    if args.weak_prompt:
        PROFILE = "weak"
        WEAK = True
        args.no_few_shot = True
    else:
        PROFILE = args.prompt_profile
        WEAK = PROFILE == "weak"
        if PROFILE == "weak":
            args.no_few_shot = True

    # Lazy API setup — only runs when main() is called, not on import
    load_project_env()

    try:
        client = create_client()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    test_cases_path = (
        args.test_cases.resolve() if args.test_cases.is_absolute() else (root / args.test_cases).resolve()
    )
    few_shot_path = args.few_shot.resolve() if args.few_shot.is_absolute() else (root / args.few_shot).resolve()

    with open(test_cases_path, encoding="utf-8") as f:
        test_cases = json.load(f)

    few_shot_block = ""
    if not args.no_few_shot:
        # structure_only uses a sanitized few-shot file with no EVSLA vocab
        if PROFILE == "structure_only":
            fs_path = default_structure_only_few_shot_path(root)
        else:
            fs_path = few_shot_path
        examples = load_few_shot_samples(fs_path)
        few_shot_block = format_few_shot_block(examples)
        if examples:
            print(f"Loaded {len(examples)} few-shot example(s) from {fs_path}")
        else:
            print(f"No few-shot examples loaded (missing or empty: {fs_path})")

    output_dir = output_path_for_case(root, "TC000").parent
    output_dir.mkdir(parents=True, exist_ok=True)
    reset_usage_ledger(token_usage_path(root), "online")

    if not kge_ready():
        print(
            "--- KGE context disabled: missing kge_data/ (run `pip install -r requirements.txt` "
            "then `python -m kge.train` with GRAPHRAG_API_KEY or OPENAI_API_KEY) ---"
        )

    # 處理 test_cases.json 中的全部案例
    written = 0
    for tc in test_cases:
        print(f"\n>>> Processing {tc['id']}: {tc['nl_intent']}")

        kge_context = build_context_for_case(tc["nl_intent"], tc["id"], root)

        turtle_result = generate_turtle_code(
            tc["nl_intent"],
            tc["id"],
            few_shot_block,
            kge_context=kge_context or None,
        )

        if turtle_result:
            file_path = output_path_for_case(root, tc["id"])
            file_path.write_text(turtle_result, encoding="utf-8")
            written += 1
            print(f"Successfully saved Turtle to: {file_path}")
            print("-" * 30)
            print(turtle_result)
            print("-" * 30)

    ensure_complete_generation(written, len(test_cases), output_dir)

if __name__ == "__main__":
    main()
