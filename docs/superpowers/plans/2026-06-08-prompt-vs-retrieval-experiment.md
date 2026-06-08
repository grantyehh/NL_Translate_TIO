# Prompt Knowledge vs Retrieval Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a trustworthy hub-and-spoke EVSLA evaluator, token/latency instrumentation, six controlled knowledge configurations, 30 gold test cases, and a one-pass pilot workflow.

**Architecture:** Keep generation, evaluation, and reporting separate. `experiment_cases.py` validates gold cases, `strict_evaluator.py` canonicalizes JSON-LD into comparable semantic facts and validates ontology usage, and `run_metrics.py` records API tokens and stage timings. Existing pipeline entry points receive an explicit configuration instead of duplicating new scripts.

**Tech Stack:** Python 3.13, `unittest`, `rdflib`, OpenAI Python SDK, NumPy/PyKEEN for existing KGE artifacts, JSON and Turtle fixtures.

---

## File Structure

- Create `experiment_cases.py`: gold-case schema validation and loading.
- Create `strict_evaluator.py`: semantic canonicalization, matching, ontology validation, and scoring.
- Create `run_metrics.py`: unified token and latency event ledger.
- Create `compare_prompt_retrieval.py`: aggregate quality, token, and latency reports.
- Create `experiment_cases_30.json`: 30 manually reviewed EVSLA cases.
- Create `prompts/structure_only_example.json`: placeholder-only structural example.
- Create `prompts/prompt_profiles.py`: Full Prompt, Hybrid-lite, and Retrieval-only prompt builders.
- Create `tests/fixtures/strict_evaluator/`: correct and intentionally corrupted JSON-LD fixtures.
- Create `tests/test_experiment_cases.py`.
- Create `tests/test_strict_evaluator.py`.
- Create `tests/test_run_metrics.py`.
- Create `tests/test_prompt_profiles.py`.
- Create `tests/test_compare_prompt_retrieval.py`.
- Modify `token_usage.py`: preserve compatibility while delegating new records to `run_metrics.py`.
- Modify `evsla_prompt.py`: separate structural rules from concrete EVSLA mappings.
- Modify `LLM-only/nl_to_tio.py`: support `full_prompt` and `structure_only`.
- Modify `GraphRag/nl_to_tio.py`: support `hybrid_lite` and `retrieval_only`, and record stage timings.
- Modify `KGE/KGE-based-graphrag/nl_to_tio.py`: support `hybrid_lite` and `retrieval_only`, and record stage timings.
- Modify `GraphRag/subgraph_retriever.py`: expose seed, embedding, graph traversal, and serialization timings.
- Modify `KGE/KGE-based-graphrag/kge/retrieve.py`: expose embedding and local retrieval timings.
- Create `run_prompt_retrieval_experiment.py`: run selected cells, repeats, and cases.
- Modify `run_all_experiments.py`: leave legacy Phase 1 behavior intact and point users to the new runner.

### Task 1: Gold Case Schema

**Files:**
- Create: `experiment_cases.py`
- Create: `tests/test_experiment_cases.py`

- [ ] **Step 1: Write failing schema tests**

```python
def test_load_case_accepts_hub_spoke_gold():
    case = validate_case({
        "id": "TC101",
        "category": "evsla_grounding",
        "nl_intent": "企業A總部至台中分點的延遲低於50ms。",
        "tenant": {"name": "企業A", "ontology_type": "evsla:Tenant"},
        "service": {"ontology_type": "evsla:EnterpriseVpnService"},
        "topology": {
            "ontology_type": "evsla:HubAndSpokeTopology",
            "hub": {"name": "總部", "ontology_type": "evsla:HubSite"},
            "spokes": [{"name": "台中分點", "ontology_type": "evsla:SpokeSite"}],
        },
        "requirements": [{
            "metric": "evsla:latency",
            "operator": "LESS_THAN",
            "threshold": {"value": 50, "unit": "ms"},
            "statistic": None,
            "scope": "evsla:specificSpoke",
            "applies_to_spokes": ["台中分點"],
            "measurement_method": None,
            "time_window": None,
        }],
        "must_not_emit": ["evsla:jitter"],
        "allowed_defaults": [],
    })
    assert case["id"] == "TC101"


def test_validate_case_rejects_unknown_metric():
    case = valid_case()
    case["requirements"][0]["metric"] = "evsla:jitter"
    with self.assertRaisesRegex(ValueError, "unknown EVSLA term"):
        validate_case(case)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python3 -m unittest tests.test_experiment_cases -v
```

Expected: import failure because `experiment_cases.py` does not exist.

- [ ] **Step 3: Implement strict validation**

Implement:

```python
REQUIRED_CATEGORIES = {"evsla_grounding", "semantic_composition", "evsla_structure"}
REQUIREMENT_FIELDS = {
    "metric", "operator", "threshold", "statistic", "scope",
    "applies_to_spokes", "measurement_method", "time_window",
}

def load_known_curies(ttl_dir: Path = TTL_DIR) -> set[str]:
    graph = Graph()
    for ttl_path in sorted(ttl_dir.glob("*.ttl")):
        graph.parse(ttl_path, format="turtle")
    return {
        graph.namespace_manager.normalizeUri(node)
        for node in set(graph.subjects()) | set(graph.predicates()) | set(graph.objects())
        if isinstance(node, URIRef)
    }

def validate_case(case: dict[str, Any], known_curies: set[str] | None = None) -> dict[str, Any]:
    known_curies = known_curies or load_known_curies()
    if case.get("category") not in REQUIRED_CATEGORIES:
        raise ValueError("unknown category")
    topology = case.get("topology") or {}
    spoke_names = {item["name"] for item in topology.get("spokes", [])}
    if not topology.get("hub") or not spoke_names:
        raise ValueError("hub and at least one spoke are required")
    for requirement in case.get("requirements", []):
        if set(requirement) != REQUIREMENT_FIELDS:
            raise ValueError("requirement fields do not match schema")
        for key in ("metric", "statistic", "scope", "measurement_method", "time_window"):
            value = requirement.get(key)
            if value is not None and value not in known_curies:
                raise ValueError(f"unknown EVSLA term: {value}")
        if not set(requirement["applies_to_spokes"]).issubset(spoke_names):
            raise ValueError("requirement references a spoke outside topology")
    return case

def load_cases(path: Path) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    cases = [validate_case(row) for row in rows]
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case id")
    return cases
```

Validation must reject duplicate IDs, missing hub/spokes, requirements with
missing keys, unknown CURIEs, metric spokes outside the topology, and categories
other than the three declared suites.

- [ ] **Step 4: Run tests**

Run:

```bash
python3 -m unittest tests.test_experiment_cases -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add experiment_cases.py tests/test_experiment_cases.py
git commit -m "feat(eval): add EVSLA gold case schema"
```

### Task 2: Semantic Canonicalization and Matching

**Files:**
- Create: `strict_evaluator.py`
- Create: `tests/test_strict_evaluator.py`
- Create: `tests/fixtures/strict_evaluator/TC101_correct.jsonld`
- Create: `tests/fixtures/strict_evaluator/TC101_wrong_threshold.jsonld`
- Create: `tests/fixtures/strict_evaluator/TC101_wrong_spoke.jsonld`
- Create: `tests/fixtures/strict_evaluator/TC101_unknown_curie.jsonld`

- [ ] **Step 1: Write failing canonicalization tests**

```python
def test_reordered_expectations_match_same_gold():
    score = evaluate_document(reordered_two_metric_doc(), two_metric_gold(), ontology())
    self.assertEqual(score["requirement_exact_match"], 1.0)


def test_wrong_spoke_pairing_lowers_requirement_f1():
    score = evaluate_document(wrong_spoke_doc(), two_metric_gold(), ontology())
    self.assertLess(score["requirement_field_f1"], 1.0)
    self.assertIn("SEMANTIC_SPOKE_MISMATCH", score["errors"])


def test_invented_metric_increases_hallucination_rate():
    score = evaluate_document(extra_metric_doc(), one_metric_gold(), ontology())
    self.assertGreater(score["hallucination_rate"], 0.0)
```

- [ ] **Step 2: Run tests and verify failure**

```bash
python3 -m unittest tests.test_strict_evaluator -v
```

Expected: import failure because `strict_evaluator.py` does not exist.

- [ ] **Step 3: Implement canonical data types**

Implement immutable records:

```python
@dataclass(frozen=True)
class Requirement:
    metric: str | None
    operator: str | None
    value: int | float | None
    unit: str | None
    statistic: str | None
    scope: str | None
    applies_to_spokes: tuple[str, ...]
    measurement_method: str | None
    time_window: str | None


@dataclass(frozen=True)
class SemanticDocument:
    tenant: str | None
    hub: str | None
    spokes: tuple[str, ...]
    service_type: str | None
    topology_type: str | None
    requirements: tuple[Requirement, ...]
```

Implement:

```python
def canonicalize_document(doc: dict[str, Any]) -> SemanticDocument:
    topology = next(
        (item for item in doc.get("intentContext", [])
         if item.get("ontologyType") == "evsla:HubAndSpokeTopology"),
        {},
    )
    requirements = tuple(
        canonicalize_target(target)
        for expectation in doc.get("intentExpectation", [])
        for target in expectation.get("expectationTarget", [])
    )
    return SemanticDocument(
        tenant=(doc.get("tenant") or {}).get("name"),
        hub=(topology.get("evsla:hasHub") or {}).get("name"),
        spokes=tuple(sorted(
            item.get("name", "") for item in topology.get("evsla:hasSpoke", [])
        )),
        service_type=first_service_type(doc),
        topology_type=topology.get("ontologyType"),
        requirements=requirements,
    )

def requirement_distance(gold: Requirement, actual: Requirement) -> int:
    return sum(
        gold_value != actual_value
        for gold_value, actual_value in zip(astuple(gold), astuple(actual))
    )

def match_requirements(
    gold: tuple[Requirement, ...],
    actual: tuple[Requirement, ...],
) -> tuple[tuple[int, int], ...]:
    candidates = permutations(range(len(actual)), min(len(gold), len(actual)))
    best = min(
        candidates,
        key=lambda order: sum(
            requirement_distance(gold[i], actual[j])
            for i, j in enumerate(order)
        ),
        default=(),
    )
    return tuple(enumerate(best))
```

Use exhaustive permutation matching because each case has at most four
requirements. Do not add a new optimization dependency.

- [ ] **Step 4: Implement semantic scores**

Implement:

```python
def evaluate_semantics(actual: SemanticDocument, gold: SemanticDocument) -> dict[str, Any]:
    entity_counts = score_entity_facts(actual, gold)
    requirement_counts = score_requirement_fields(actual, gold)
    errors = collect_semantic_errors(actual, gold)
    return {
        "entity_topology_precision": precision(entity_counts),
        "entity_topology_recall": recall(entity_counts),
        "entity_topology_f1": f1(entity_counts),
        "requirement_field_precision": precision(requirement_counts),
        "requirement_field_recall": recall(requirement_counts),
        "requirement_field_f1": f1(requirement_counts),
        "requirement_exact_match": exact_requirement_ratio(actual, gold),
        "hallucination_rate": hallucination_ratio(actual, gold),
        "errors": errors,
    }
```

Null gold fields are not required facts. An actual non-null value for a null
gold field counts as an invented fact unless listed in `allowed_defaults`.

- [ ] **Step 5: Run tests**

```bash
python3 -m unittest tests.test_strict_evaluator -v
```

Expected: semantic tests pass.

- [ ] **Step 6: Commit**

```bash
git add strict_evaluator.py tests/test_strict_evaluator.py tests/fixtures/strict_evaluator
git commit -m "feat(eval): score EVSLA semantic faithfulness"
```

### Task 3: Ontology Validity

**Files:**
- Modify: `strict_evaluator.py`
- Modify: `tests/test_strict_evaluator.py`

- [ ] **Step 1: Write failing ontology tests**

```python
def test_unknown_evsla_jitter_is_rejected():
    score = evaluate_document(jitter_doc(), one_metric_gold(), ontology())
    self.assertEqual(score["ontology_validity"], 0.0)
    self.assertIn("ONTOLOGY_UNKNOWN_CURIE", score["errors"])


def test_has_hub_requires_hub_site():
    score = evaluate_document(spoke_as_hub_doc(), one_metric_gold(), ontology())
    self.assertIn("ONTOLOGY_RANGE_VIOLATION", score["errors"])


def test_metric_must_be_rdf_property():
    score = evaluate_document(class_as_metric_doc(), one_metric_gold(), ontology())
    self.assertIn("ONTOLOGY_ROLE_MISMATCH", score["errors"])
```

- [ ] **Step 2: Run tests and verify failure**

```bash
python3 -m unittest tests.test_strict_evaluator -v
```

Expected: ontology-specific assertions fail.

- [ ] **Step 3: Implement ontology index**

Implement:

```python
@dataclass(frozen=True)
class OntologyIndex:
    curie_to_uri: dict[str, URIRef]
    classes: frozenset[str]
    properties: frozenset[str]
    instance_types: dict[str, frozenset[str]]
    domains: dict[str, frozenset[str]]
    ranges: dict[str, frozenset[str]]


def load_ontology_index(ttl_dir: Path) -> OntologyIndex:
    graph = load_merged_graph(ttl_dir)
    return OntologyIndex(
        curie_to_uri=collect_curies(graph),
        classes=frozenset(collect_classes(graph)),
        properties=frozenset(collect_properties(graph)),
        instance_types=collect_instance_types(graph),
        domains=collect_domains(graph),
        ranges=collect_ranges(graph),
    )
```

Resolve `rdf:type`, `rdfs:subClassOf`, `rdfs:subPropertyOf`, `rdfs:domain`, and
`rdfs:range`. Validate explicit EVSLA output fields against this index.

- [ ] **Step 4: Add ontology scores to `evaluate_document`**

Return:

```python
{
    "ontology_assertion_count": total,
    "ontology_valid_assertion_count": valid,
    "ontology_validity": valid / total if total else 0.0,
    "unknown_curies": sorted(unknown_curies),
    "role_mismatches": role_mismatches,
    "domain_range_violations": domain_range_violations,
}
```

- [ ] **Step 5: Run evaluator tests**

```bash
python3 -m unittest tests.test_strict_evaluator -v
```

Expected: all semantic and ontology tests pass.

- [ ] **Step 6: Commit**

```bash
git add strict_evaluator.py tests/test_strict_evaluator.py
git commit -m "feat(eval): validate EVSLA ontology semantics"
```

### Task 4: Unified Token and Latency Ledger

**Files:**
- Create: `run_metrics.py`
- Create: `tests/test_run_metrics.py`
- Modify: `token_usage.py`

- [ ] **Step 1: Write failing ledger tests**

```python
def test_stage_timer_records_elapsed_ms():
    ledger = MetricsLedger(path, run_id="pilot-1", configuration="full_prompt")
    with ledger.stage(case_id="TC101", repeat=1, ledger="online", stage="generation_api"):
        pass
    row = json.loads(path.read_text())[0]
    self.assertGreaterEqual(row["elapsed_ms"], 0.0)


def test_api_usage_and_timing_share_dimensions():
    ledger.record_api_call(
        case_id="TC101", repeat=1, ledger="online",
        stage="jsonld_generation", model="gpt-5.4",
        api="chat.completions", response=response, elapsed_ms=12.5,
    )
    self.assertEqual(load_rows(path)[0]["total_tokens"], 18)
```

- [ ] **Step 2: Run tests and verify failure**

```bash
python3 -m unittest tests.test_run_metrics -v
```

- [ ] **Step 3: Implement event schema and timer**

Implement this public API:

```python
ledger = MetricsLedger(
    path=Path("experiment_metrics/pilot/events.json"),
    run_id="pilot",
    configuration="hybrid_lite_graphrag",
    technical_line="graphrag",
)
with ledger.stage(
    case_id="TC101",
    repeat=1,
    ledger="online",
    stage="graph_retrieval",
):
    context = build_subgraph_context(nl_intent)
ledger.record_api_call(
    case_id="TC101",
    repeat=1,
    ledger="online",
    stage="jsonld_generation",
    model="gpt-5.4",
    api="chat.completions",
    response=response,
    elapsed_ms=elapsed_ms,
)
```

Every row contains `run_id`, `configuration`, `technical_line`, `case_id`,
`repeat`, `ledger`, `stage`, token counts, `elapsed_ms`, and `error`.
Use `time.perf_counter_ns()`.

- [ ] **Step 4: Preserve old token helpers**

Keep `extract_usage`, `load_usage_file`, and `aggregate_usage` callable by old
tests. Add aggregation for:

```python
generation_tokens
retrieval_tokens
online_total_tokens
median_case_end_to_end_ms
p95_case_end_to_end_ms
```

- [ ] **Step 5: Run tests**

```bash
python3 -m unittest tests.test_run_metrics tests.test_token_usage -v
```

- [ ] **Step 6: Commit**

```bash
git add run_metrics.py token_usage.py tests/test_run_metrics.py tests/test_token_usage.py
git commit -m "feat(metrics): record token and latency events"
```

### Task 5: Prompt Profiles

**Files:**
- Create: `prompts/__init__.py`
- Create: `prompts/prompt_profiles.py`
- Create: `prompts/structure_only_example.json`
- Create: `tests/test_prompt_profiles.py`
- Modify: `evsla_prompt.py`

- [ ] **Step 1: Write failing prompt leakage tests**

```python
def test_hybrid_lite_contains_no_concrete_mapping():
    prompt = build_system_prompt("TC101", "hybrid_lite")
    forbidden = {"evsla:latency", "evsla:p95", "evsla:twamp", "evsla:hubToAllSpokes"}
    self.assertTrue(forbidden.isdisjoint(prompt.split()))


def test_full_prompt_keeps_current_evsla_mapping():
    prompt = build_system_prompt("TC101", "full_prompt")
    self.assertIn("evsla:latency", prompt)


def test_structure_example_uses_placeholders():
    block = build_few_shot_block("hybrid_lite")
    self.assertIn("<METRIC_CURIE>", block)
    self.assertNotIn("evsla:latency", block)
```

- [ ] **Step 2: Run tests and verify failure**

```bash
python3 -m unittest tests.test_prompt_profiles -v
```

- [ ] **Step 3: Split prompt builders**

Implement:

```python
CONFIGURATIONS = {
    "full_prompt",
    "structure_only",
    "hybrid_lite",
    "retrieval_only",
}

def build_system_prompt(tc_id: str, configuration: str) -> str:
    profile = PROMPT_PROFILES[configuration]
    return render_system_prompt(tc_id=tc_id, **profile)

def build_few_shot_block(configuration: str, full_examples_path: Path) -> str:
    if configuration == "full_prompt":
        return format_full_examples(full_examples_path)
    if configuration in {"structure_only", "hybrid_lite"}:
        return STRUCTURE_EXAMPLE_PATH.read_text(encoding="utf-8")
    return ""
```

`full_prompt` retains the current behavior. `structure_only` and `hybrid_lite`
must produce byte-identical system/few-shot content. `retrieval_only` includes
only the output contract and no example.

- [ ] **Step 4: Run tests**

```bash
python3 -m unittest tests.test_prompt_profiles -v
```

- [ ] **Step 5: Commit**

```bash
git add prompts evsla_prompt.py tests/test_prompt_profiles.py
git commit -m "feat(prompt): add controlled knowledge profiles"
```

### Task 6: Instrument LLM-only, GraphRAG, and KGE

**Files:**
- Modify: `LLM-only/nl_to_tio.py`
- Modify: `LLM-only/test_nl_to_tio.py`
- Modify: `GraphRag/nl_to_tio.py`
- Modify: `GraphRag/subgraph_retriever.py`
- Modify: `GraphRag/test_nl_to_tio.py`
- Modify: `KGE/KGE-based-graphrag/nl_to_tio.py`
- Modify: `KGE/KGE-based-graphrag/kge/retrieve.py`
- Modify: `KGE/KGE-based-graphrag/test_nl_to_tio.py`

- [ ] **Step 1: Add failing CLI and timing tests**

Test that:

```text
LLM-only accepts: full_prompt, structure_only
GraphRAG accepts: hybrid_lite, retrieval_only
KGE accepts: hybrid_lite, retrieval_only
```

Mock API callers and assert each case records `prompt_build`,
`jsonld_generation`, and `case_end_to_end`. GraphRAG additionally records
`seed_selection`, `grounding_embedding`, and `graph_retrieval`; KGE records
`retrieval_embedding` and `kge_retrieval`.

- [ ] **Step 2: Run pipeline unit tests and verify failure**

```bash
python3 -m unittest \
  LLM-only/test_nl_to_tio.py \
  GraphRag/test_nl_to_tio.py \
  KGE/KGE-based-graphrag/test_nl_to_tio.py -v
```

- [ ] **Step 3: Add common CLI arguments**

Each entry point accepts:

```text
--configuration
--run-id
--repeat
--metrics-out
--output-dir
```

Reject configurations unsupported by that technical line.

- [ ] **Step 4: Instrument stages**

Wrap actual work, not placeholder sleeps:

```python
with metrics.stage(
    case_id=tc_id,
    repeat=args.repeat,
    ledger="online",
    stage="prompt_build",
):
    system_prompt = build_system_prompt(tc_id, args.configuration)

start = time.perf_counter_ns()
response = client.chat.completions.create(
    model=CHAT_MODEL,
    messages=messages,
    temperature=0,
)
elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
metrics.record_api_call(
    case_id=tc_id,
    repeat=args.repeat,
    ledger="online",
    stage="jsonld_generation",
    model=CHAT_MODEL,
    api="chat.completions",
    response=response,
    elapsed_ms=elapsed_ms,
)
```

GraphRAG local BFS and serialization are `graph_retrieval`; KGE NumPy ranking,
neighborhood expansion, link prediction, and formatting are `kge_retrieval`.

- [ ] **Step 5: Run pipeline tests**

Use the command from Step 2. Expected: all pass without network calls.

- [ ] **Step 6: Commit**

```bash
git add LLM-only GraphRag KGE/KGE-based-graphrag
git commit -m "feat(experiment): instrument prompt retrieval pipelines"
```

### Task 7: Create and Validate the 30 Cases

**Files:**
- Create: `experiment_cases_30.json`
- Modify: `tests/test_experiment_cases.py`

- [ ] **Step 1: Add dataset-level failing tests**

```python
def test_experiment_dataset_has_balanced_categories():
    cases = load_cases(ROOT / "experiment_cases_30.json")
    counts = Counter(case["category"] for case in cases)
    self.assertEqual(counts, {
        "evsla_grounding": 10,
        "semantic_composition": 10,
        "evsla_structure": 10,
    })


def test_no_case_exposes_evsla_curie_in_natural_language():
    for case in load_cases(ROOT / "experiment_cases_30.json"):
        self.assertNotIn("evsla:", case["nl_intent"])
```

- [ ] **Step 2: Run dataset tests and verify failure**

```bash
python3 -m unittest tests.test_experiment_cases -v
```

- [ ] **Step 3: Author the 30 cases**

Use the PPT semantics and current TTL vocabulary only:

```text
metrics: latency, packetLoss, guaranteedBandwidth
statistics: p95, p99, average, maximum, minimum
scopes: hubToAllSpokes, perSpoke, specificSpoke
methods: activeMeasurement, twamp
windows: fiveMinuteWindow, oneHourWindow, monthlySlaWindow
```

At least six semantic-composition cases contain two or more requirements, and at
least four cases assign different metrics to different named spokes. Do not use
jitter as a required metric.

- [ ] **Step 4: Validate and manually inspect**

```bash
python3 -m unittest tests.test_experiment_cases -v
python3 -c 'from pathlib import Path; from experiment_cases import load_cases; print(len(load_cases(Path("experiment_cases_30.json"))))'
```

Expected: tests pass and output is `30`.

- [ ] **Step 5: Commit**

```bash
git add experiment_cases_30.json tests/test_experiment_cases.py
git commit -m "testdata: add 30 EVSLA experiment cases"
```

### Task 8: Runner and Comparison Report

**Files:**
- Create: `run_prompt_retrieval_experiment.py`
- Create: `compare_prompt_retrieval.py`
- Create: `tests/test_compare_prompt_retrieval.py`
- Modify: `run_all_experiments.py`

- [ ] **Step 1: Write failing runner/report tests**

Test that `--dry-run` emits exactly six cells, that `--repeats 1` schedules 180
case runs, and that reports aggregate by configuration and category.

```python
def test_dry_run_schedules_six_cells():
    jobs = build_jobs(cases=[case], repeats=1)
    self.assertEqual({job.configuration for job in jobs}, {
        "full_prompt", "structure_only",
        "hybrid_lite_graphrag", "hybrid_lite_kge",
        "retrieval_only_graphrag", "retrieval_only_kge",
    })
```

- [ ] **Step 2: Run tests and verify failure**

```bash
python3 -m unittest tests.test_compare_prompt_retrieval -v
```

- [ ] **Step 3: Implement runner**

Support:

```text
--cases experiment_cases_30.json
--repeats 1|3
--cells <list>
--from-case <case-id>
--resume
--dry-run
--run-id
```

Write outputs under:

```text
experiment_outputs/<run_id>/<configuration>/repeat_<n>/TC*.jsonld
experiment_metrics/<run_id>/events.json
experiment_reports/<run_id>/
```

Do not overwrite legacy `jsonld_outputs/` or `phase1/`.

- [ ] **Step 4: Implement comparison report**

Generate JSON and text summaries with:

```text
requirement_field_f1
case_exact_match
ontology_validity
hallucination_rate
avg_online_tokens_per_case
amortized_tokens_per_case@30,@100,@1000
median_end_to_end_ms
p95_end_to_end_ms
replacement_quality_delta
retrieval_information_gain
token_multiplier
latency_multiplier
```

- [ ] **Step 5: Run tests**

```bash
python3 -m unittest tests.test_compare_prompt_retrieval tests.test_run_all_experiments -v
```

- [ ] **Step 6: Commit**

```bash
git add run_prompt_retrieval_experiment.py compare_prompt_retrieval.py \
  tests/test_compare_prompt_retrieval.py run_all_experiments.py
git commit -m "feat(experiment): add prompt retrieval runner"
```

### Task 9: Offline Verification Gate

**Files:**
- No new files.

- [ ] **Step 1: Run the complete offline suite**

```bash
python3 -m unittest discover -v
```

Expected: all tests pass with zero API calls.

- [ ] **Step 2: Validate the execution matrix**

```bash
python3 run_prompt_retrieval_experiment.py --dry-run --repeats 1
```

Expected: 180 scheduled runs, six cells, 30 cases, no output generation.

- [ ] **Step 3: Run strict evaluator fixtures**

```bash
python3 strict_evaluator.py \
  --cases experiment_cases_30.json \
  --outputs tests/fixtures/strict_evaluator \
  --out /tmp/strict-evaluator-fixtures.json
```

Expected: each fixture reports its declared error code and the correct fixture
has `case_exact_match: true`.

- [ ] **Step 4: Commit any verification-only corrections**

```bash
git add -u
git commit -m "test: verify prompt retrieval experiment"
```

### Task 10: One-Pass API Pilot

**Files:**
- Generated artifacts only under `experiment_outputs/`, `experiment_metrics/`,
  and `experiment_reports/`.

- [ ] **Step 1: Confirm environment without printing secrets**

```bash
test -n "${GRAPHRAG_API_KEY:-${OPENAI_API_KEY:-}}" && echo "API key available"
```

Expected: `API key available`.

- [ ] **Step 2: Run one case across all six cells**

```bash
python3 run_prompt_retrieval_experiment.py \
  --repeats 1 \
  --from-case TC101 \
  --limit 1 \
  --run-id pilot-smoke
```

Expected: six JSON-LD outputs, token events, stage timings, and no missing cell.

- [ ] **Step 3: Evaluate smoke outputs**

```bash
python3 compare_prompt_retrieval.py --run-id pilot-smoke
```

Expected: six report rows with nonzero online tokens and end-to-end latency.

- [ ] **Step 4: Run the 30-case one-pass pilot**

```bash
python3 run_prompt_retrieval_experiment.py \
  --repeats 1 \
  --run-id pilot-30
python3 compare_prompt_retrieval.py --run-id pilot-30
```

Expected: 180 outputs and complete quality/token/latency reports.

- [ ] **Step 5: Review pilot before repeats**

Verify:

```text
all 180 jobs have output or an explicit error
all cells have token and latency events
no prompt leakage test failed
strict evaluator produced no internal errors
GraphRAG and KGE retrieval contexts are non-empty
```

Only after this gate, run repeats 2 and 3 with `--resume --repeats 3`.
