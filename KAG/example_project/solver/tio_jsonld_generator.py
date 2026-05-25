import json
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
            "KAG graph variables:\n"
            f"{json.dumps(graph_data, ensure_ascii=False, indent=2, default=str)}"
        )

    return "\n\n".join(block for block in task_blocks if block.strip())


@PromptABC.register("tio_jsonld_generator_prompt")
class TIOJsonldGeneratorPrompt(PromptABC):
    template_en = """You are the final generator inside a KAG solver pipeline for the TIO Experiment.

Use the KAG solver context below as grounded evidence. Generate only one valid TIO JSON-LD object for the current network intent.

Hard requirements:
- Output JSON only. Do not wrap it in markdown.
- Top-level @type must be "Intent".
- Use the API-friendly JSON-LD contract with id, name, description, intentOwner, intentExpectation, intentContext, and intentReport.
- Prefer EVSLA/TIO terms supported by the KAG context, such as evsla:EnterpriseVpnSlaIntent, evsla:EnterpriseVpnService, evsla:SlaExpectation, evsla:latency, evsla:packetLoss, evsla:guaranteedBandwidth, evsla:p95, evsla:p99, evsla:minimum, evsla:hubToAllSpokes, evsla:specificSpoke, evsla:twamp, evsla:activeMeasurement, and evsla:fiveMinuteWindow.
- Do not invent ontology URIs that are not supported by the KAG context or the TIO prompt requirements.

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
        return True

    def parse_response(self, response: Any, **kwargs):
        if isinstance(response, dict):
            if isinstance(response.get("jsonld"), dict):
                response = response["jsonld"]
            return json.dumps(response, ensure_ascii=False, indent=2)
        if isinstance(response, str):
            return response.strip()
        raise ValueError(f"Unsupported TIO JSON-LD response: {response!r}")


@GeneratorABC.register("tio_jsonld_generator")
class TIOJsonldGenerator(GeneratorABC):
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
