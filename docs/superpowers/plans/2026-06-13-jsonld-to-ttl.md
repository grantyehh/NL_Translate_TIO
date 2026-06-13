# JSON-LD → Turtle 輸出遷移 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把成熟的 EVSLA hub-and-spoke 實驗線從 API-friendly JSON-LD 輸出改回 TIO Turtle,保留全部方法邏輯,完全不動 `tio-agent/`。

**Architecture:** 輸出契約集中在 `evsla_prompt.py`(所有 pipeline 共用),所以格式改寫主要落在這一支 + 各 `nl_to_tio.py` 的「輸出路徑/few-shot 欄位」。評估器以 `codex/ttl-kag:evaluate_ttl.py` 的 rdflib-turtle 解析為核心,套上新版 `<experiment_key>` CLI 與報告鍵。few-shot 依新版 4 個 hub-and-spoke 範例手寫成 Turtle。

**Tech Stack:** Python 3.13、openai、rdflib、unittest;模型 `gpt-5.4`。

**分支:** 已在 `codex/jsonld-to-ttl`(基於 `codex/jsonld-snapshot-20260613`),spec 已 commit(`d8152a5`)。

**慣例:** 測試用 `unittest`(專案無 pytest)。每個 pipeline 測試以 `cd <dir> && python3 -m unittest test_nl_to_tio` 執行。根層測試以 `python3 -m unittest tests.<name>`。

---

## 真實述詞對照表(手寫 Turtle / prompt 依據)

JSON-LD(API-friendly)→ Turtle(真實 CURIE):

| JSON-LD 欄位 | Turtle 述詞/型別 |
|---|---|
| `@type: "Intent"` | `a icm:Intent` |
| `intentExpectation` | `icm:intentElements`(Intent→Expectation) |
| `intentContext` | `icm:intentElements`(Intent→Context) |
| `@type: "PropertyExpectation"` | `a icm:PropertyExpectation` |
| `expectationTarget` | `icm:target`(Expectation→Target) |
| `@type: "Context"` | `a icm:Context` |
| `targetProperty` / `evsla:hasMetric` | `evsla:hasMetric <evsla:metric>` |
| `targetValue` | `icm:valuesOfTargetProperty [ a quan:Quantity ; rdf:value N ; quan:unit "u" ]` |
| `evsla:hasThreshold` | `evsla:hasThreshold [ a quan:Quantity ; rdf:value N ; quan:unit "u" ]` |
| `evsla:hasStatistic/Scope/MeasurementMethod/TimeWindow` | 同名 `evsla:` 述詞,值為 `evsla:` 個體 |
| `expectationObject`(Service) | `a evsla:EnterpriseVpnService ; evsla:forTenant ex:tenant` |
| `tenant` | `ex:tenant a evsla:Tenant ; rdfs:label "<name>"@zh` |
| `intentContext` 的 hub/spoke | `evsla:hasHub [ a evsla:HubSite ; rdfs:label .. ]`、`evsla:hasSpoke [ a evsla:SpokeSite ; .. ]`、`a evsla:HubAndSpokeTopology` |

前綴(固定):
```
@prefix icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .
@prefix quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex:    <http://example.org/tio-instance/FS-EVSLA-NN/> .
```
> 註:`evsla:` 的 base IRI 以 `TM Forum Intent Ontology/EnterpriseVpnSlaOntology.ttl` 內 `@prefix evsla:` 宣告為準;Task 1 第 1 步先 grep 確認。

---

## File Structure

| 檔案 | 變更 | 責任 |
|---|---|---|
| `evsla_prompt.py` | 改寫 | 系統 prompt 從 JSON-LD 契約 → Turtle 契約 |
| `few_shot_samples.json` | 改寫 | 4 例 `jsonld` 欄位 → `turtle` 欄位 |
| `LLM-only/nl_to_tio.py` | 修改 | 輸出 `tio_outputs/llm_only/*.ttl`、few-shot 讀 `turtle` |
| `GraphRag/nl_to_tio.py` | 修改 | 同上(`graphrag`) |
| `KGE/KGE-based-graphrag/nl_to_tio.py` | 修改 | 同上(`kge`,root 深一層) |
| `KAG/nl_to_tio.py` | 修改 | 輸出 `tio_outputs/kag/*.ttl`、turtle generator |
| `KAG/example_project/solver/tio_turtle_generator.py` | 新增 | 移植自 ttl-kag,取代 `tio_jsonld_generator.py` |
| `evaluate_ttl.py` | 新增 | rdflib-turtle 評估 + key-based CLI |
| `evaluate_jsonld.py` | 刪除 | 由 evaluate_ttl 取代 |
| `run_all_experiments.py` | 修改 | `PHASE1_EVALUATOR = evaluate_ttl.py` |
| `*/test_nl_to_tio.py` | 修改 | 斷言翻成 Turtle 契約 |
| `tests/` 周邊測試 | 修改 | 路徑/評估器改 ttl |

---

## Task 1: 改寫 `evsla_prompt.py` 為 Turtle 契約

**Files:**
- Modify: `evsla_prompt.py:14-58`(`build_evsla_system_prompt` 回傳字串)
- Test: 由 `LLM-only/test_nl_to_tio.py` 的 prompt 斷言覆蓋(Task 4 翻新)

- [ ] **Step 1: 確認 evsla base IRI**

Run:
```bash
grep -nE "@prefix evsla:" "TM Forum Intent Ontology/EnterpriseVpnSlaOntology.ttl"
```
Expected: 一行 `@prefix evsla: <...EnterpriseVpnSlaOntology/> .` —— 用它替換對照表中的 base IRI(若不同)。

- [ ] **Step 2: 改寫 `build_evsla_system_prompt` 回傳字串**

把 `evsla_prompt.py:14-58` 的 `return f"""..."""` 整段換成:

```python
    return f"""You generate TIO Turtle (RDF) for Enterprise VPN hub-and-spoke SLA intents only.
Output ONLY valid, parseable Turtle. Never output JSON, JSON-LD, Markdown, prose, 5G slices, datacenter fabric, or generic service delivery.

Required @prefix declarations (always include all of them):
@prefix icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .
@prefix quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex:    <http://example.org/tio-instance/{tc_id.lower()}/> .

Graph structure:
- ex:intent a icm:Intent ; icm:intentElements <each expectation>, <the topology context> ; rdfs:comment "<concise English SLA summary>"@en .
- ex:intent has tenant: ex:tenant a evsla:Tenant ; rdfs:label "<tenant>"@zh .
- One ex:service a evsla:EnterpriseVpnService ; evsla:forTenant ex:tenant .
- One PropertyExpectation per SLA metric:
    ex:exp-<metric> a icm:PropertyExpectation, evsla:SlaExpectation ;
      icm:target ex:tgt-<metric> ;
      rdfs:comment "<what this guarantees>"@en .
- Each target:
    ex:tgt-<metric> a icm:Target ;
      evsla:hasMetric evsla:<metric> ;
      icm:valuesOfTargetProperty [ a quan:Quantity ; rdf:value <number> ; quan:unit "<unit>" ] ;
      evsla:hasThreshold [ a quan:Quantity ; rdf:value <number> ; quan:unit "<unit>" ] ;
      evsla:hasStatistic evsla:<stat> ;
      evsla:hasScope evsla:<scope> ;
      evsla:hasMeasurementMethod evsla:<method> ;
      evsla:hasTimeWindow evsla:fiveMinuteWindow .
- Hub-and-spoke context:
    ex:topology a icm:Context, evsla:HubAndSpokeTopology ;
      evsla:hasHub [ a evsla:HubSite ; rdfs:label "<hub>"@zh ] ;
      evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label "<spoke>"@zh ] ;
      ... one evsla:hasSpoke per spoke ... .

Metric mappings:
- latency -> evsla:latency, LESS_THAN, evsla:twamp
- packet_loss / 封包遺失率 -> evsla:packetLoss, LESS_THAN, evsla:twamp
- guaranteed_bandwidth / 保證頻寬 -> evsla:guaranteedBandwidth, GREATER_THAN_OR_EQUAL, evsla:minimum, evsla:activeMeasurement
- 95% -> evsla:p95
- 99% -> evsla:p99
- all spokes / 所有分點 / 各Spoke -> evsla:hubToAllSpokes
- named single spoke / 指定單一 Spoke -> evsla:specificSpoke
- default time window -> evsla:fiveMinuteWindow

Target rules:
- evsla:hasMetric and the metric used in icm:valuesOfTargetProperty/evsla:hasThreshold must be consistent.
- Both icm:valuesOfTargetProperty and evsla:hasThreshold must carry a quan:Quantity with rdf:value (number) and quan:unit (string).

{retrieval_note}Core semantics must be carried by triples, not only by rdfs:comment.
"""
```

> 註:`build_evsla_graphrag_query`(line 61+)不動 —— 它只是 retrieval query,仍可回傳 evsla CURIE。

- [ ] **Step 3: 編譯檢查**

Run: `python3 -c "import ast; ast.parse(open('evsla_prompt.py').read()); print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add evsla_prompt.py
git commit -m "feat(prompt): switch evsla system prompt from JSON-LD to Turtle contract"
```

---

## Task 2: 手寫 Turtle few-shot(`few_shot_samples.json`)

**Files:**
- Modify: `few_shot_samples.json`(整檔)
- Test: `tests/test_few_shot_turtle.py`(新增)

- [ ] **Step 1: 寫 few-shot 可解析測試(先失敗)**

Create `tests/test_few_shot_turtle.py`:

```python
import json
import unittest
from pathlib import Path

from rdflib import Graph

ROOT = Path(__file__).resolve().parent.parent
FEW_SHOT = ROOT / "few_shot_samples.json"
PREFIXES = """@prefix icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .
@prefix quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
"""


class TestFewShotTurtle(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(FEW_SHOT.read_text(encoding="utf-8"))
        self.examples = self.data["examples"]

    def test_examples_use_turtle_field_not_jsonld(self) -> None:
        for ex in self.examples:
            self.assertIn("turtle", ex)
            self.assertNotIn("jsonld", ex)

    def test_each_turtle_parses_and_has_core_elements(self) -> None:
        for ex in self.examples:
            ttl = ex["turtle"]
            # few-shot 範例自帶 @prefix;若缺則補上共用前綴再解析
            body = ttl if "@prefix ex:" in ttl else PREFIXES + ttl
            g = Graph()
            g.parse(data=body, format="turtle")
            text = g.serialize(format="turtle")
            for needle in ("IntentCommonModel/Intent", "IntentCommonModel/PropertyExpectation",
                           "IntentCommonModel/Target", "IntentCommonModel/Context",
                           "valuesOfTargetProperty"):
                self.assertIn(needle, text, f"{ex['pattern']} missing {needle}")


if __name__ == "__main__":
    unittest.main()
```

Run: `python3 -m unittest tests.test_few_shot_turtle -v`
Expected: FAIL(目前 examples 還有 `jsonld` 欄位)

- [ ] **Step 2: 改寫 `few_shot_samples.json`**

整檔換成(4 例,`jsonld`→`turtle`;`description` 改 turtle 版):

```json
{
  "description": "Few-shot examples for EnterpriseVpnSlaOntology (evsla) hub-and-spoke enterprise VPN SLA intents, expressed as TIO Turtle. The LLM sees pattern, nl_intent, and turtle; learn the icm:/evsla:/quan: graph structure, not the literal content.",
  "examples": [
    {
      "pattern": "evsla_latency_p95_hub_to_all_spokes",
      "nl_intent": "確保安捷銀行總部至所有分點之延遲在95%的時間內低於50ms。",
      "turtle": "@prefix icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .\n@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .\n@prefix quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .\n@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .\n@prefix ex:    <http://example.org/tio-instance/FS-EVSLA-01/> .\n\nex:intent a icm:Intent ;\n  icm:intentElements ex:exp-latency, ex:topology ;\n  rdfs:comment \"Assure hub-to-all-spokes latency SLA for 安捷銀行 enterprise VPN.\"@en .\nex:tenant a evsla:Tenant ; rdfs:label \"安捷銀行\"@zh .\nex:service a evsla:EnterpriseVpnService ; evsla:forTenant ex:tenant .\nex:exp-latency a icm:PropertyExpectation, evsla:SlaExpectation ;\n  icm:target ex:tgt-latency ;\n  rdfs:comment \"Latency must stay below 50 ms at p95 across all spokes.\"@en .\nex:tgt-latency a icm:Target ;\n  evsla:hasMetric evsla:latency ;\n  icm:valuesOfTargetProperty [ a quan:Quantity ; rdf:value 50 ; quan:unit \"ms\" ] ;\n  evsla:hasThreshold [ a quan:Quantity ; rdf:value 50 ; quan:unit \"ms\" ] ;\n  evsla:hasStatistic evsla:p95 ;\n  evsla:hasScope evsla:hubToAllSpokes ;\n  evsla:hasMeasurementMethod evsla:twamp ;\n  evsla:hasTimeWindow evsla:fiveMinuteWindow .\nex:topology a icm:Context, evsla:HubAndSpokeTopology ;\n  evsla:hasHub [ a evsla:HubSite ; rdfs:label \"台北總部\"@zh ] ;\n  evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label \"新竹分行\"@zh ] ;\n  evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label \"台中分行\"@zh ] ;\n  evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label \"高雄分行\"@zh ] .\n"
    },
    {
      "pattern": "evsla_packet_loss_p99_hub_to_all_spokes",
      "nl_intent": "確保遠辰製造Hub與各Spoke間封包遺失率低於0.1%（99%時間）。",
      "turtle": "@prefix icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .\n@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .\n@prefix quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .\n@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .\n@prefix ex:    <http://example.org/tio-instance/FS-EVSLA-02/> .\n\nex:intent a icm:Intent ;\n  icm:intentElements ex:exp-packet-loss, ex:topology ;\n  rdfs:comment \"Assure hub-to-all-spokes packet loss SLA for 遠辰製造 enterprise VPN.\"@en .\nex:tenant a evsla:Tenant ; rdfs:label \"遠辰製造\"@zh .\nex:service a evsla:EnterpriseVpnService ; evsla:forTenant ex:tenant .\nex:exp-packet-loss a icm:PropertyExpectation, evsla:SlaExpectation ;\n  icm:target ex:tgt-packet-loss ;\n  rdfs:comment \"Packet loss must stay below 0.1% at p99 across all spokes.\"@en .\nex:tgt-packet-loss a icm:Target ;\n  evsla:hasMetric evsla:packetLoss ;\n  icm:valuesOfTargetProperty [ a quan:Quantity ; rdf:value 0.1 ; quan:unit \"%\" ] ;\n  evsla:hasThreshold [ a quan:Quantity ; rdf:value 0.1 ; quan:unit \"%\" ] ;\n  evsla:hasStatistic evsla:p99 ;\n  evsla:hasScope evsla:hubToAllSpokes ;\n  evsla:hasMeasurementMethod evsla:twamp ;\n  evsla:hasTimeWindow evsla:fiveMinuteWindow .\nex:topology a icm:Context, evsla:HubAndSpokeTopology ;\n  evsla:hasHub [ a evsla:HubSite ; rdfs:label \"桃園總廠\"@zh ] ;\n  evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label \"新竹廠\"@zh ] ;\n  evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label \"台中廠\"@zh ] ;\n  evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label \"台南廠\"@zh ] .\n"
    },
    {
      "pattern": "evsla_minimum_bandwidth_specific_spoke",
      "nl_intent": "提供宏達物流總部至高雄倉儲中心100Mbps以上保證頻寬。",
      "turtle": "@prefix icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .\n@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .\n@prefix quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .\n@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .\n@prefix ex:    <http://example.org/tio-instance/FS-EVSLA-03/> .\n\nex:intent a icm:Intent ;\n  icm:intentElements ex:exp-bandwidth, ex:topology ;\n  rdfs:comment \"Assure minimum guaranteed bandwidth to a specific spoke for 宏達物流 enterprise VPN.\"@en .\nex:tenant a evsla:Tenant ; rdfs:label \"宏達物流\"@zh .\nex:service a evsla:EnterpriseVpnService ; evsla:forTenant ex:tenant .\nex:exp-bandwidth a icm:PropertyExpectation, evsla:SlaExpectation ;\n  icm:target ex:tgt-bandwidth ;\n  rdfs:comment \"Guaranteed bandwidth must be at least 100 Mbps to the named spoke.\"@en .\nex:tgt-bandwidth a icm:Target ;\n  evsla:hasMetric evsla:guaranteedBandwidth ;\n  icm:valuesOfTargetProperty [ a quan:Quantity ; rdf:value 100 ; quan:unit \"Mbps\" ] ;\n  evsla:hasThreshold [ a quan:Quantity ; rdf:value 100 ; quan:unit \"Mbps\" ] ;\n  evsla:hasStatistic evsla:minimum ;\n  evsla:hasScope evsla:specificSpoke ;\n  evsla:hasMeasurementMethod evsla:activeMeasurement ;\n  evsla:hasTimeWindow evsla:fiveMinuteWindow .\nex:topology a icm:Context, evsla:HubAndSpokeTopology ;\n  evsla:hasHub [ a evsla:HubSite ; rdfs:label \"台北營運總部\"@zh ] ;\n  evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label \"高雄倉儲中心\"@zh ] .\n"
    },
    {
      "pattern": "evsla_multi_metric_hub_to_spokes",
      "nl_intent": "確保精準醫材台北研發總部至竹北實驗室與台南製造廠之延遲在95%的時間內低於35ms，且Hub與各Spoke間封包遺失率低於0.05%（99%時間）。",
      "turtle": "@prefix icm:   <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .\n@prefix evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/> .\n@prefix quan:  <http://tio.models.tmforum.org/tio/v3.6.0/QuantityOntology/> .\n@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .\n@prefix ex:    <http://example.org/tio-instance/FS-EVSLA-04/> .\n\nex:intent a icm:Intent ;\n  icm:intentElements ex:exp-latency, ex:exp-packet-loss, ex:topology ;\n  rdfs:comment \"Assure latency and packet loss SLA hub-to-all-spokes for 精準醫材 enterprise VPN.\"@en .\nex:tenant a evsla:Tenant ; rdfs:label \"精準醫材\"@zh .\nex:service a evsla:EnterpriseVpnService ; evsla:forTenant ex:tenant .\nex:exp-latency a icm:PropertyExpectation, evsla:SlaExpectation ;\n  icm:target ex:tgt-latency ;\n  rdfs:comment \"Latency must stay below 35 ms at p95 across all spokes.\"@en .\nex:tgt-latency a icm:Target ;\n  evsla:hasMetric evsla:latency ;\n  icm:valuesOfTargetProperty [ a quan:Quantity ; rdf:value 35 ; quan:unit \"ms\" ] ;\n  evsla:hasThreshold [ a quan:Quantity ; rdf:value 35 ; quan:unit \"ms\" ] ;\n  evsla:hasStatistic evsla:p95 ;\n  evsla:hasScope evsla:hubToAllSpokes ;\n  evsla:hasMeasurementMethod evsla:twamp ;\n  evsla:hasTimeWindow evsla:fiveMinuteWindow .\nex:exp-packet-loss a icm:PropertyExpectation, evsla:SlaExpectation ;\n  icm:target ex:tgt-packet-loss ;\n  rdfs:comment \"Packet loss must stay below 0.05% at p99 across all spokes.\"@en .\nex:tgt-packet-loss a icm:Target ;\n  evsla:hasMetric evsla:packetLoss ;\n  icm:valuesOfTargetProperty [ a quan:Quantity ; rdf:value 0.05 ; quan:unit \"%\" ] ;\n  evsla:hasThreshold [ a quan:Quantity ; rdf:value 0.05 ; quan:unit \"%\" ] ;\n  evsla:hasStatistic evsla:p99 ;\n  evsla:hasScope evsla:hubToAllSpokes ;\n  evsla:hasMeasurementMethod evsla:twamp ;\n  evsla:hasTimeWindow evsla:fiveMinuteWindow .\nex:topology a icm:Context, evsla:HubAndSpokeTopology ;\n  evsla:hasHub [ a evsla:HubSite ; rdfs:label \"台北研發總部\"@zh ] ;\n  evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label \"竹北實驗室\"@zh ] ;\n  evsla:hasSpoke [ a evsla:SpokeSite ; rdfs:label \"台南製造廠\"@zh ] .\n"
    }
  ]
}
```

- [ ] **Step 3: 跑測試,應通過**

Run: `python3 -m unittest tests.test_few_shot_turtle -v`
Expected: PASS(2 tests)

- [ ] **Step 4: Commit**

```bash
git add few_shot_samples.json tests/test_few_shot_turtle.py
git commit -m "feat(few-shot): convert hub-and-spoke examples from JSON-LD to Turtle"
```

---

## Task 3: 新增 `evaluate_ttl.py`(rdflib-turtle 核心 + key-based CLI)

**Files:**
- Create: `evaluate_ttl.py`
- Delete: `evaluate_jsonld.py`
- Test: `tests/test_evaluate_ttl.py`(新增)

- [ ] **Step 1: 取得 ttl-kag 的 turtle 評估核心**

Run:
```bash
git show "codex/ttl-kag:evaluate_ttl.py" > /tmp/evaluate_ttl_ref.py
wc -l /tmp/evaluate_ttl_ref.py
```
Expected: 344 行。此檔含 `evaluate_file(path, expected_elements, case_id, ...)`、`load_reference_vocabulary`、`expand_curie`、rdflib parse。**保留這些 helper**,只換掉 `main()`/CLI。

- [ ] **Step 2: 寫評估器測試(先失敗)**

Create `tests/test_evaluate_ttl.py`:

```python
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_eval():
    path = ROOT / "evaluate_ttl.py"
    spec = importlib.util.spec_from_file_location("evaluate_ttl", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestEvaluateTtl(unittest.TestCase):
    def test_experiments_map_has_four_keys_and_ttl_dirs(self) -> None:
        ev = load_eval()
        self.assertEqual(set(ev.EXPERIMENTS.keys()), {"llm_only", "graphrag", "kge", "kag"})
        for key, cfg in ev.EXPERIMENTS.items():
            self.assertTrue(str(cfg["outputs_dir"]).endswith(f"tio_outputs/{key}"))

    def test_evaluate_file_reports_expected_coverage(self) -> None:
        ev = load_eval()
        ttl = (
            "@prefix icm: <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .\n"
            "@prefix ex: <http://example.org/x/> .\n"
            "ex:i a icm:Intent ; icm:intentElements ex:e .\n"
            "ex:e a icm:PropertyExpectation ; icm:target ex:t .\n"
            "ex:t a icm:Target ; icm:valuesOfTargetProperty ex:v .\n"
        )
        tmp = ROOT / "tio_outputs" / "llm_only"
        tmp.mkdir(parents=True, exist_ok=True)
        f = tmp / "TCTEST.ttl"
        f.write_text(ttl, encoding="utf-8")
        try:
            row = ev.evaluate_file(f, ["icm:Intent", "icm:PropertyExpectation", "icm:Target", "icm:valuesOfTargetProperty"], "TCTEST")
            self.assertTrue(row["parse_ok"])
            self.assertEqual(row["expected_coverage_ratio"], 1.0)
        finally:
            f.unlink()


if __name__ == "__main__":
    unittest.main()
```

Run: `python3 -m unittest tests.test_evaluate_ttl -v`
Expected: FAIL(`evaluate_ttl.py` 不存在)

- [ ] **Step 3: 建立 `evaluate_ttl.py`**

以 `/tmp/evaluate_ttl_ref.py` 為基礎複製到 `evaluate_ttl.py`,然後:

(a) 保留其 rdflib parse / `evaluate_file` / `load_reference_vocabulary` / `expand_curie` 等 helper。

(b) `load_reference_vocabulary` 載入的 ontology 目錄須包含新 evsla 檔。確認其 glob `*.ttl` 指向 `TM Forum Intent Ontology/`(含 `EnterpriseVpnSlaOntology.ttl`)。若 ref 版指向別處,改成:
```python
ONTOLOGY_DIR = ROOT / "TM Forum Intent Ontology"
```

(c) 把 ref 版的 `main()`(`--outputs-dir/--json-out` CLI)整段刪除,改成新版 key-based 介面。在檔尾加入:

```python
ROOT = Path(__file__).resolve().parent

EXPERIMENTS = {
    "llm_only": {"label": "LLM-only", "outputs_dir": ROOT / "tio_outputs" / "llm_only",
                 "report": ROOT / "phase1" / "phase1_llm_only.json"},
    "graphrag": {"label": "GraphRAG", "outputs_dir": ROOT / "tio_outputs" / "graphrag",
                 "report": ROOT / "phase1" / "phase1_graphrag.json"},
    "kge": {"label": "KGE", "outputs_dir": ROOT / "tio_outputs" / "kge",
            "report": ROOT / "phase1" / "phase1_kge.json"},
    "kag": {"label": "KAG", "outputs_dir": ROOT / "tio_outputs" / "kag",
            "report": ROOT / "phase1" / "phase1_kag.json"},
}


def test_cases_path() -> Path:
    return ROOT / "test_cases_20.json"


def evaluate_experiment(experiment_key: str, test_cases: list[dict]) -> Path:
    config = EXPERIMENTS[experiment_key]
    outputs_dir = config["outputs_dir"]
    reports = []
    for tc in test_cases:
        tc_id = tc["id"]
        path = outputs_dir / f"{tc_id}.ttl"
        if not path.is_file():
            reports.append({"case_id": tc_id, "parse_ok": False,
                            "parse_error": f"missing file: {path}",
                            "triple_count": 0, "expected_results": [],
                            "expected_coverage_ratio": None})
            continue
        reports.append(evaluate_file(path, tc.get("expected_tio_elements", []), tc_id))

    print(f"\n## {config['label']}")
    for row in reports:
        print(f"=== {row['case_id']} ===")
        print(f"  parse_ok: {row['parse_ok']}")
        if row.get("parse_error"):
            print(f"  parse_error: {row['parse_error']}")
        cov = row.get("expected_coverage_ratio")
        if cov is not None:
            print(f"  expected_tio_elements_met: {cov * 100:.0f}%")
    report_path = config["report"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(reports, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote JSON report to {report_path}")
    return report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shared phase-1 evaluator for generated TIO Turtle.")
    parser.add_argument("experiment", nargs="?",
                        choices=tuple(EXPERIMENTS.keys()) + ("all",), default="all")
    args = parser.parse_args(argv)
    cases = json.loads(test_cases_path().read_text(encoding="utf-8"))
    keys = list(EXPERIMENTS.keys()) if args.experiment == "all" else [args.experiment]
    for key in keys:
        evaluate_experiment(key, cases)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

> 註:`evaluate_file` 的回傳須含 `case_id`、`parse_ok`、`parse_error`、`expected_coverage_ratio`(ref 版已有這些鍵)。若 ref 版 `evaluate_file` 簽名為 `(path, expected, case_id, ontology_terms=..., ...)`,多餘參數給預設即可。

- [ ] **Step 4: 跑測試,應通過**

Run: `python3 -m unittest tests.test_evaluate_ttl -v`
Expected: PASS(2 tests)

- [ ] **Step 5: 刪除舊評估器**

```bash
git rm evaluate_jsonld.py
```

- [ ] **Step 6: Commit**

```bash
git add evaluate_ttl.py tests/test_evaluate_ttl.py
git commit -m "feat(eval): add turtle phase-1 evaluator with key-based CLI; drop evaluate_jsonld"
```

---

## Task 4: `LLM-only/nl_to_tio.py` 改輸出 Turtle

**Files:**
- Modify: `LLM-only/nl_to_tio.py`(行號見下)
- Test: `LLM-only/test_nl_to_tio.py`

- [ ] **Step 1: 翻新測試斷言(先失敗)**

在 `LLM-only/test_nl_to_tio.py` 做以下替換:

`test_format_few_shot_block_uses_json_ld_examples` 整個方法換成:
```python
    def test_format_few_shot_block_uses_turtle_examples(self) -> None:
        examples = [{"pattern": "p", "nl_intent": "x",
                     "turtle": "ex:i a icm:Intent ."}]
        block = nl_to_tio.format_few_shot_block(examples)
        self.assertIn("Turtle:", block)
        self.assertIn("a icm:Intent", block)
        self.assertNotIn("JSON-LD:", block)
```

`test_output_path_uses_jsonld_outputs_and_extension` →:
```python
    def test_output_path_uses_tio_outputs_and_ttl(self) -> None:
        root = Path("/tmp/example/CHT/LLM-only")
        expected = Path("/tmp/example/CHT/tio_outputs/llm_only/TC001.ttl")
        self.assertEqual(nl_to_tio.output_path_for_case(root, "TC001"), expected)
```

`test_system_prompt_requires_json_ld_not_turtle` →:
```python
    def test_system_prompt_requires_turtle_not_json_ld(self) -> None:
        prompt = nl_to_tio.build_system_prompt("TC001")
        self.assertIn("Turtle", prompt)
        self.assertIn("icm:PropertyExpectation", prompt)
        self.assertNotIn("JSON-LD", prompt)
```

`test_system_prompt_requires_enterprise_vpn_sla_ontology_terms` 內,把 `self.assertIn("intentExpectation", prompt)` 那類 JSON 欄位斷言移除,保留 evsla 詞彙斷言;`self.assertNotIn("DeliveryExpectation", prompt)` 保留。

`test_generate_jsonld_code_records_token_usage`:把 mock content `'{"@context": {}}'` 改成 `"ex:i a icm:Intent ."`,斷言 `result` 對應改;方法可改名 `test_generate_turtle_records_token_usage` 並呼叫 `nl_to_tio.generate_turtle_code`(下步會建立此別名指向新函式)。stage 斷言 `rows[0]["stage"]` 改為 `"turtle_generation"`。

Run: `cd LLM-only && python3 -m unittest test_nl_to_tio -v`
Expected: FAIL

- [ ] **Step 2: 改 `format_few_shot_block`(`LLM-only/nl_to_tio.py:47-61`)**

```python
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
```

- [ ] **Step 3: 改 `output_path_for_case`(`:64-65`)**

```python
def output_path_for_case(root: Path, tc_id: str) -> Path:
    return root.parent / "tio_outputs" / "llm_only" / f"{tc_id}.ttl"
```

- [ ] **Step 4: 改生成函式(`:77-125`)**

把 `generate_jsonld_code` 改名 `generate_turtle_code`,內文字串與 stage 改 turtle:
- print 改 `f"--- Translating to TIO Turtle format for {tc_id} ---"`
- `few_shot_section` 標題改「【Few-shot Turtle 範例（與本題不同情境；請學結構，勿抄內容）】」
- `user_content` 結尾改「請直接生成對應的 TIO Turtle。」
- `record_usage(... stage="turtle_generation" ...)`
- 檔尾相容別名:`generate_jsonld_code = generate_turtle_code`(保留向後相容,若無人引用可省略)

- [ ] **Step 5: 改 `main()` 內輸出敘述(`:128-186`)**

- argparse help 文字 `Few-shot NL+JSON-LD examples...` → `Few-shot NL+Turtle examples...`、`NL to TIO JSON-LD via LLM only.` → `NL to TIO Turtle via LLM only.`
- few-shot 載入 print「No few-shot examples」訊息不變。
- 迴圈內變數 `jsonld_result` → `turtle_result`,呼叫 `generate_turtle_code(...)`;`print(f"Successfully saved JSON-LD to ...")` → `Turtle`。

- [ ] **Step 6: 跑測試,應通過**

Run: `cd LLM-only && python3 -m unittest test_nl_to_tio -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add LLM-only/nl_to_tio.py LLM-only/test_nl_to_tio.py
git commit -m "feat(llm-only): emit TIO Turtle to tio_outputs"
```

---

## Task 5: `GraphRag/nl_to_tio.py` 改輸出 Turtle

**Files:**
- Modify: `GraphRag/nl_to_tio.py`、`GraphRag/test_nl_to_tio.py`

- [ ] **Step 1: 對照 LLM-only 找出對應點**

Run:
```bash
grep -nE "jsonld|JSON-LD|output_path_for_case|format_few_shot_block|generate_jsonld_code|stage=" GraphRag/nl_to_tio.py
```
Expected: 列出 GraphRag 版的對應行(輸出子目錄為 `graphrag`)。

- [ ] **Step 2: 翻新測試斷言(先失敗)**

依 `GraphRag/test_nl_to_tio.py` 既有 jsonld 斷言,套 Task 4 Step 1 同樣的翻法:few-shot 改 `Turtle:`、output path 改 `tio_outputs/graphrag/TC001.ttl`、prompt 改 Turtle、stage 改 `turtle_generation`。

Run: `cd GraphRag && python3 -m unittest test_nl_to_tio -v`
Expected: FAIL

- [ ] **Step 3: 套用程式改動**

同 Task 4 Step 2-5,差別:
- `output_path_for_case` 子目錄 `"graphrag"`。
- 保留 GraphRag 特有的 retrieval(rdflib typed traversal context)邏輯不動,只改「序列化/輸出/few-shot 欄位/stage 字串」。

- [ ] **Step 4: 跑測試,應通過**

Run: `cd GraphRag && python3 -m unittest test_nl_to_tio -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add GraphRag/nl_to_tio.py GraphRag/test_nl_to_tio.py
git commit -m "feat(graphrag): emit TIO Turtle to tio_outputs"
```

---

## Task 6: `KGE/KGE-based-graphrag/nl_to_tio.py` 改輸出 Turtle

**Files:**
- Modify: `KGE/KGE-based-graphrag/nl_to_tio.py`、`KGE/KGE-based-graphrag/test_nl_to_tio.py`

- [ ] **Step 1: 找對應點**

Run:
```bash
grep -nE "jsonld|JSON-LD|output_path_for_case|format_few_shot_block|generate_jsonld_code|stage=" KGE/KGE-based-graphrag/nl_to_tio.py
```
Expected: KGE 版對應行;注意 `output_path_for_case` 用 `root.parent.parent`(深一層)。

- [ ] **Step 2: 翻新測試斷言(先失敗)**

套 Task 4 Step 1 同樣翻法;output path 期望 `tio_outputs/kge/TC001.ttl`(`root.parent.parent`)。

Run: `cd KGE/KGE-based-graphrag && python3 -m unittest test_nl_to_tio -v`
Expected: FAIL

- [ ] **Step 3: 套用程式改動**

```python
def output_path_for_case(root: Path, tc_id: str) -> Path:
    return root.parent.parent / "tio_outputs" / "kge" / f"{tc_id}.ttl"
```
其餘同 Task 4 Step 2/4/5;保留 KGE retrieval(text grounding / TransE / link prediction)邏輯不動。

- [ ] **Step 4: 跑測試,應通過**

Run: `cd KGE/KGE-based-graphrag && python3 -m unittest test_nl_to_tio -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add KGE/KGE-based-graphrag/nl_to_tio.py KGE/KGE-based-graphrag/test_nl_to_tio.py
git commit -m "feat(kge): emit TIO Turtle to tio_outputs"
```

---

## Task 7: KAG 改輸出 Turtle(generator 移植)

**Files:**
- Create: `KAG/example_project/solver/tio_turtle_generator.py`(移植自 ttl-kag)
- Delete: `KAG/example_project/solver/tio_jsonld_generator.py`
- Modify: `KAG/nl_to_tio.py`、`KAG/test_nl_to_tio.py`、`KAG/example_project/solver/__init__.py`

- [ ] **Step 1: 取得 ttl-kag 的 turtle generator**

Run:
```bash
git show "codex/ttl-kag:KAG/example_project/solver/tio_turtle_generator.py" > KAG/example_project/solver/tio_turtle_generator.py
grep -nE "register|class |Turtle|jsonld" KAG/example_project/solver/tio_turtle_generator.py
```
Expected: 含 `@PromptABC.register("tio_turtle_generator_prompt")` 與 `@GeneratorABC.register("tio_turtle_generator")`,無 jsonld 字眼。

- [ ] **Step 2: 翻新 KAG 測試(先失敗)**

`KAG/test_nl_to_tio.py`:
- `test_generate_jsonld_code_delegates_to_kag_solver` → 改名 `test_generate_turtle_code_delegates_to_kag_solver`,mock 回傳 `"ex:i a icm:Intent ."`,呼叫 `nl_to_tio.generate_turtle_code(...)`,斷言 result 對應。
- `test_ensure_jsonld_contract_adds_missing_intent_report`:KAG 的 JSON contract fallback 在 turtle 下不適用 —— 改為 `test_solver_config_uses_turtle_generator`,斷言 solver 設定字串含 `tio_turtle_generator`、不含 `tio_jsonld_generator`(沿用既有對 config 的讀法)。
- output path 期望 `tio_outputs/kag/TC001.ttl`。

Run: `cd KAG && python3 -m unittest test_nl_to_tio -v`
Expected: FAIL

- [ ] **Step 3: 改 `KAG/nl_to_tio.py`**

- `output_path_for_case`(`:62-63`)→ `TIO_EXPERIMENT_ROOT / "tio_outputs" / "kag" / f"{tc_id}.ttl"`。
- `format_few_shot_block`(`:85-97`)讀 `turtle` 欄位、標題 `Turtle:`(同 Task 4 Step 2)。
- `generate_jsonld_code` → `generate_turtle_code`;solver generator 名稱由 `tio_jsonld_generator` 改 `tio_turtle_generator`。
- 移除/停用 `ensure_jsonld_contract`(JSON 專用);若 KAG generator 已直接吐 turtle,寫檔前不再做 JSON 契約補洞。
- 檔頭 docstring 的 `JSON-LD`/`.jsonld` 字眼改 Turtle/.ttl。

- [ ] **Step 4: 更新 solver `__init__.py` 與刪除舊 generator**

```bash
grep -rn "tio_jsonld_generator" KAG/example_project/solver/__init__.py
```
把 `__init__.py` 內 import/註冊由 `tio_jsonld_generator` 改 `tio_turtle_generator`,然後:
```bash
git rm KAG/example_project/solver/tio_jsonld_generator.py
```
同時確認 `kag_config`(template/yaml)內 generator 名稱也指向 `tio_turtle_generator`:
```bash
grep -rn "tio_jsonld_generator\|tio_turtle_generator" KAG/example_project/
```

- [ ] **Step 5: 跑測試,應通過**

Run: `cd KAG && python3 -m unittest test_nl_to_tio -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add KAG/
git commit -m "feat(kag): generate TIO Turtle via turtle generator"
```

---

## Task 8: `run_all_experiments.py` 切到 Turtle

**Files:**
- Modify: `run_all_experiments.py`、`tests/test_run_all_experiments.py`

- [ ] **Step 1: 翻新 runner 測試(先失敗)**

`tests/test_run_all_experiments.py`:斷言 `PHASE1_EVALUATOR` 指向 `evaluate_ttl.py`(非 `evaluate_jsonld.py`);若有檢查方法數/標籤的測試,確認仍為四方法。

Run: `python3 -m unittest tests.test_run_all_experiments -v`
Expected: FAIL

- [ ] **Step 2: 改 `run_all_experiments.py:11`**

```python
PHASE1_EVALUATOR = ROOT / "evaluate_ttl.py"
```
並把 `EXPERIMENTS` 內任何 `jsonld_outputs`/`.jsonld` 路徑字眼改 `tio_outputs`/`.ttl`(若 runner 直接引用輸出路徑)。

- [ ] **Step 3: 跑測試,應通過**

Run: `python3 -m unittest tests.test_run_all_experiments -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add run_all_experiments.py tests/test_run_all_experiments.py
git commit -m "feat(runner): evaluate via evaluate_ttl over tio_outputs"
```

---

## Task 9: 周邊測試與殘留清理

**Files:**
- Modify: `tests/test_token_usage.py`、`tests/test_compare_token_usage.py`、任何引用 `evaluate_jsonld`/`jsonld_outputs` 的測試

- [ ] **Step 1: 掃殘留**

Run:
```bash
grep -rIl "evaluate_jsonld\|jsonld_outputs\|\.jsonld\|generate_jsonld_code\|JSON-LD" . | grep -v tio-agent/ | grep -vE "\.git/|jsonld_outputs/"
```
Expected: 列出仍需處理的檔(預期只剩測試 / 少數 docstring)。

- [ ] **Step 2: 逐檔改 ttl 路徑/評估器引用**

把上一步列出的(排除 `tio-agent/`)逐一改:`jsonld_outputs`→`tio_outputs`、`.jsonld`→`.ttl`、`evaluate_jsonld`→`evaluate_ttl`、JSON-LD 字眼→Turtle。`token_usage` 的 stage 名稱若被斷言,改 `turtle_generation`。

- [ ] **Step 3: 跑全測試,應全綠**

Run:
```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
for t in LLM-only GraphRag KGE/KGE-based-graphrag KAG; do (cd "$t" && python3 -m unittest test_nl_to_tio); done
python3 -m unittest discover -s tests -p "test_*.py"
```
Expected: 全部 OK,無 FAIL/ERROR。

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: purge residual JSON-LD references outside tio-agent"
```

---

## Task 10: 端到端離線驗收

**Files:** 無(僅執行驗證)

- [ ] **Step 1: 確認 tio-agent 未被改**

Run: `git diff --name-only codex/jsonld-snapshot-20260613..HEAD -- tio-agent/`
Expected: 空輸出(完全沒動 tio-agent)。

- [ ] **Step 2: 全測試總跑**

Run:
```bash
for t in LLM-only GraphRag KGE/KGE-based-graphrag KAG; do echo "[$t]"; (cd "$t" && python3 -m unittest test_nl_to_tio 2>&1 | tail -3); done
python3 -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -5
```
Expected: 全 OK。

- [ ] **Step 3: 評估器對 few-shot turtle 冒煙測試**

把一個 few-shot turtle 寫成檔丟給評估器跑覆蓋(驗證 evsla 不被判未知、icm 覆蓋計算正確):
```bash
python3 -c "
import json, pathlib
d=json.load(open('few_shot_samples.json'))
out=pathlib.Path('tio_outputs/llm_only'); out.mkdir(parents=True, exist_ok=True)
(out/'TC001.ttl').write_text(d['examples'][0]['turtle'], encoding='utf-8')
print('wrote smoke ttl')
"
python3 evaluate_ttl.py llm_only 2>&1 | grep -A2 "TC001"
```
Expected: `parse_ok: True`,且 `expected_tio_elements_met` 有非零覆蓋(TC001 expected 為 icm:Intent/PropertyExpectation/Target/Context/valuesOfTargetProperty,few-shot[0] 全具備 → 100%)。事後刪除冒煙檔。

- [ ] **Step 4(可選,需 API key + KAG 環境):實跑生成**

```bash
cd LLM-only && python3 nl_to_tio.py --test-cases ../test_cases_20.json
```
Expected: `tio_outputs/llm_only/TC*.ttl` 生成且可被 evaluate_ttl 解析。

- [ ] **Step 5: 收尾選項**

實作完成後,依 superpowers:finishing-a-development-branch 決定 merge / PR / 後續。

---

## 驗收標準(對應 spec §6)

1. 四條線單元測試全綠,斷言為 Turtle 契約。 → Task 4-7
2. 四條線可產出 `tio_outputs/<method>/TC*.ttl`,rdflib 可 parse。 → Task 4-7, 10
3. `evaluate_ttl.py` 對 hub-spoke 輸出能算覆蓋,evsla 不判未知。 → Task 3, 10-S3
4. `run_all_experiments.py` 端到端可跑出 `phase1/phase1_<method>.json`。 → Task 8, 10
5. 全 repo(排除 tio-agent)無殘留誤導性 JSON-LD 輸出。 → Task 9
6. `tio-agent/` 未被修改。 → Task 10-S1
