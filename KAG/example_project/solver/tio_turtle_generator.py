from typing import Any, List

from kag.interface import GeneratorABC, LLMClient, PromptABC


def _task_context_to_text(task_context: Any) -> str:
    if not isinstance(task_context, dict):
        return str(task_context or "")

    lines = []
    name = task_context.get("name")
    task = task_context.get("task")
    result = task_context.get("result")
    thought = task_context.get("thought")
    if name or task:
        lines.append(f"{name or 'Task'}: {task or ''}".strip())
    if result:
        lines.append(f"result: {result}")
    if thought:
        lines.append(f"thought: {thought}")
    return "\n".join(lines)


def build_solver_content(context: Any) -> str:
    task_blocks = []
    for task in context.gen_task(False):
        if hasattr(task, "get_task_context"):
            task_blocks.append(_task_context_to_text(task.get_task_context()))
        else:
            task_blocks.append(str(task))

    graph_data = getattr(context, "variables_graph", None)
    if graph_data:
        task_blocks.append(
            f"KAG graph variables:\n{graph_data}"
        )

    return "\n\n".join(block for block in task_blocks if block.strip())


@PromptABC.register("tio_turtle_generator_prompt")
class TIOTurtleGeneratorPrompt(PromptABC):
    template_en = """You are the final generator inside a KAG solver pipeline for the TIO Experiment.

Use the KAG solver context below as grounded evidence. Generate only valid RDF 1.1 Turtle for the current network intent.

Hard requirements:
- Output Turtle only. Do not wrap it in markdown or add prose.
- Use official TIO v3.6.0 namespace IRIs and vocabulary supported by the KAG context.
- Include an icm:Intent instance whose URI contains the current test case ID.
- Represent requirements with icm:DeliveryExpectation or icm:PropertyExpectation and bind each expectation to an icm:Target with icm:target.
- Use icm:Context, log:Condition, and icm:valuesOfTargetProperty when required by the natural language.
- Comments may supplement structure but must not replace the required TIO classes and properties.
- Do not invent unofficial TIO predicates.

Few-shot examples for structure only:
$few_shot_block

Current test case ID: $tc_id

Natural language intent:
$query

KAG solver context:
$content
"""
    template_zh = template_en

    @property
    def template_variables(self) -> List[str]:
        return ["query", "content", "tc_id", "few_shot_block"]

    def is_json_format(self):
        return False

    def parse_response(self, response: Any, **kwargs):
        if isinstance(response, str):
            return response.strip()
        raise ValueError(f"Unsupported TIO Turtle response: {response!r}")


@GeneratorABC.register("tio_turtle_generator")
class TIOTurtleGenerator(GeneratorABC):
    def __init__(
        self,
        llm_client: LLMClient,
        generated_prompt: PromptABC,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_client = llm_client
        self.generated_prompt = generated_prompt

    def invoke(self, query, context, **kwargs):
        variables = {
            "query": query,
            "content": build_solver_content(context),
            "tc_id": kwargs.get("tc_id", ""),
            "few_shot_block": kwargs.get("few_shot_block", ""),
        }
        return self.llm_client.invoke(
            variables,
            self.generated_prompt,
            segment_name="answer",
            tag_name="Final Answer",
            with_json_parse=self.generated_prompt.is_json_format(),
        )
