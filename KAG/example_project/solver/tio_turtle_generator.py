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
You generate TIO Turtle (RDF) for Enterprise VPN hub-and-spoke SLA intents only.
Use the KAG solver context below as grounded evidence. Output ONLY valid, parseable Turtle. Never output JSON, JSON-LD, Markdown, prose, 5G slices, datacenter fabric, or generic service delivery.

Required @prefix declarations (always include all of them):
@prefix icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .
@prefix quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex:    <http://example.org/tio-instance/...test-case-id.../> .

Graph structure (the ex: namespace must embed the current test case ID):
- ex:intent a icm:Intent, evsla:EnterpriseVpnSlaIntent ; icm:intentElements <each expectation>, <the topology context> ; rdfs:comment "<concise English SLA summary>"@en .
- ex:tenant a evsla:Tenant ; rdfs:label "<tenant>"@zh .
- ex:service a evsla:EnterpriseVpnService ; evsla:forTenant ex:tenant .
- One PropertyExpectation per SLA metric:
    ex:exp-<metric> a icm:PropertyExpectation, evsla:SlaExpectation ; icm:target ex:tgt-<metric> ; rdfs:comment "<what this guarantees>"@en .
- Each target:
    ex:tgt-<metric> a icm:Target ;
      evsla:hasMetric evsla:<metric> ;
      icm:valuesOfTargetProperty [ a quan:Quantity ; rdf:value <number> ; quan:unit "<unit>" ] ;
      evsla:hasThreshold [ a quan:Quantity ; rdf:value <number> ; quan:unit "<unit>" ] ;
      evsla:hasStatistic evsla:<stat> ; evsla:hasScope evsla:<scope> ;
      evsla:hasMeasurementMethod evsla:<method> ; evsla:hasTimeWindow evsla:fiveMinuteWindow .
- Hub-and-spoke context:
    ex:topology a icm:Context, evsla:HubAndSpokeTopology ;
      evsla:hasHub [ a evsla:HubSite ; rdfs:label "<hub>"@zh ] ;
      evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label "<spoke>"@zh ] .

Metric mappings:
- latency -> evsla:latency, LESS_THAN, evsla:twamp
- packet_loss / 封包遺失率 -> evsla:packetLoss, LESS_THAN, evsla:twamp
- guaranteed_bandwidth / 保證頻寬 -> evsla:guaranteedBandwidth, GREATER_THAN_OR_EQUAL, evsla:minimum, evsla:activeMeasurement
- 95% -> evsla:p95 ; 99% -> evsla:p99
- all spokes / 所有分點 / 各Spoke -> evsla:hubToAllSpokes ; named single spoke -> evsla:specificSpoke

Comments may supplement structure but must not replace the required classes and properties. Do not invent unofficial predicates.

Comparison direction (required — encode it explicitly with TIO terms, never only in rdfs:comment):
- Also declare: @prefix log: <http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/> .
  and @prefix met: <http://tio.models.tmforum.org/tio/v3.6.0/MetricsAndObservations/> .
- Make each threshold a shared named node ex:thr-<metric> used by BOTH icm:valuesOfTargetProperty and evsla:hasThreshold (not an inline blank node).
- For every metric add a condition, and list it in ex:intent icm:intentElements:
    ex:cond-<metric> a log:Condition ; <fn> ( ex:obs-<metric>-value ex:thr-<metric> ) .
    ex:obs-<metric> a met:Observation ; met:observedMetric evsla:<metric> .
    ex:obs-<metric>-value a quan:Quantity ; met:observedValue ( ex:obs-<metric> ) .
  <fn>: latency / packet_loss -> quan:smaller ; guaranteed_bandwidth -> quan:atLeast.

Few-shot Turtle examples for structure only:
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


@PromptABC.register("tio_turtle_generator_prompt_weak")
class TIOTurtleGeneratorPromptWeak(TIOTurtleGeneratorPrompt):
    """Weak variant: no EVSLA structure / metric mappings / comparison-direction /
    TIO namespace URIs. Domain knowledge must come from the KAG solver context."""
    template_en = """You are the final generator inside a KAG solver pipeline for the TIO Experiment.
You generate TIO Turtle (RDF) for Enterprise VPN hub-and-spoke SLA intents only.
Use the KAG solver context below as grounded evidence. Output ONLY valid, parseable Turtle.
Never output JSON, JSON-LD, Markdown, prose, 5G slices, datacenter fabric, or generic service delivery.
Declare every @prefix you use so the Turtle parses. Use ex: with the current test case ID for instances.
Core semantics must be carried by triples, not only by rdfs:comment.

Current test case ID: $tc_id

Natural language intent:
$query

KAG solver context:
$content
"""
    template_zh = template_en


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
