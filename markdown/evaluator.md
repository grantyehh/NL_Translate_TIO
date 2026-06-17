# 評估器:`evaluate_ttl.py` + `semantic_eval.py`

> 本文描述四條 pipeline 共用的 phase-1 評估器,對齊原始碼。逐輪結果見 [`progress.md`](progress.md);retrieval 架構見 [`retrieval_arch.md`](retrieval_arch.md)。

評估器分兩層,都是純讀檔、不呼叫 LLM:

1. **`evaluate_ttl.py`** — 格式 / 詞彙 / 測試規格覆蓋率的「外層」檢查,逐題寫出 `phase1/phase1_<experiment>.json`。
2. **`semantic_eval.py`** — graph-binding 的「語意正確性」評分(11 維 composite),由 `evaluate_ttl` 在 parse 成功且有 gold case 時呼叫。

```text
tio_outputs/<experiment>/TC*.ttl
  → evaluate_ttl.evaluate_file(...)            外層:syntax / vocab / coverage
      → semantic_eval.score_semantics(g, gold) 內層:11 維 graph-binding composite
  → phase1/phase1_<experiment>.json
  → compare_reports.py / run_structure_experiments.py / compare_token_usage.py  比較報告
```

---

## 1. 外層:`evaluate_ttl.py`

`evaluate_file(path, expected_elements, case_id, ..., gold_case)` 對單一 TTL 輸出產出一份 dict,含以下檢查:

### 1.1 Syntax(語法)

- 先用 `strip_markdown_turtle_fence` 嘗試剝掉 ` ```turtle ` code fence(理想輸出應是 pure Turtle,但模型偶爾包 fence)。是否剝過記在 `markdown_fence_stripped`。
- 用 rdflib 以 RDF 1.1 Turtle parse;parse 失敗則 `parse_ok=False` 並記 `parse_error`,後續所有需要 graph 的檢查跳過。
- `triple_count`:成功 parse 的 triple 數。

### 1.2 Vocabulary(詞彙合法性)

參考詞表由 `load_reference_vocabulary` 從 `TM Forum Intent Ontology/*.ttl` 載入(`rdfs:Class` → classes、`rdf:Property` + `fun:Function` → properties),整份 cache 一次。

- `unknown_predicates`:輸出中用到、但**不在參考詞表**也不是標準前綴(rdf/rdfs/xsd/dcterms/skos/time)的 predicate。
- `unknown_types`:輸出中 `rdf:type` 的 object 不在參考 class 詞表(排除 w3.org)。
- `prefix_checks`:逐一比對輸出宣告的 `@prefix` 是否等於官方 IRI(`matches_official`)。

> 這層抓的是「**自創 / 非官方 namespace**」—— structure-only 地板與舊 weak 條件之所以 composite=0,根因就是吐了 `example.org/...` 之類的 IRI,在這裡會大量現形(unknown pred/type 暴增)。

### 1.3 測試規格覆蓋率(expected coverage)

對 gold case 的 `expected_tio_elements`(CURIE 清單)逐一檢查:

- 該 CURIE 展開後若是 **class** → 輸出中需有至少一個 `rdf:type` 指向它;
- 若是 **property** → 需在至少一個 triple 當 predicate 用過;
- 否則記 reason(未知 prefix / 不在參考詞表)。

`expected_coverage_ratio` = 命中數 / 總數。另有 `intent_uri_contains_case_id`:是否有某個 `rdf:type` 的 subject IRI 內含 case id(輕量 sanity hint)。

### 1.4 實驗註冊與 CLI

`EXPERIMENTS` dict 把每個 experiment key 對到 `tio_outputs/<dir>` 與 `phase1/phase1_<key>.json`,涵蓋強配方 `llm_only / graphrag / kge / kag`、`*_weak`、structure-only `graphrag_structure / kge_structure / llm_only_structure`。

```bash
python evaluate_ttl.py                              # 不帶參數 = 評全部
python evaluate_ttl.py graphrag_structure --test-cases test_cases_40.json
```

`--test-cases` 預設 `test_cases_20.json`,structure-only 實驗用 `test_cases_40.json`(含 TC021–040 hub-and-spoke)。

---

## 2. 內層:`semantic_eval.py`(11 維 graph-binding composite)

`score_semantics(graph, gold)` 不只看「詞彙存不存在」,而是沿 **intent 契約路徑**把每個 gold metric 綁定到輸出子圖,逐維度比對**正確性**。

### 2.1 Binding 抽取(`extract_bindings`)

沿契約路徑走:

```text
icm:Intent
  → icm:intentElements
  → (icm:PropertyExpectation 或 evsla:SlaExpectation)
  → 讀 SLA 綁定 predicate
```

SLA 綁定 predicate(`hasMetric` / `hasStatistic` / `hasScope` / `hasMeasurementMethod` / `hasTimeWindow`)的 `rdfs:domain` 在 ontology 是 **`evsla:SlaExpectation`**,因此 `_first_obj` **以 expectation 為權威來源,icm:Target 只當 backward-compat fallback**(這是 Architecture 5 修掉 TC025 契約鏈誤判的關鍵:scorer / few-shot / ontology domain 三方對齊)。

### 2.2 逐 metric 評分(`_score_one_metric`)

對 gold 的每個 `performance_metrics`:

| 維度 | 判定方式 |
|---|---|
| `metric` | gold `ontology_term` 是否可從 binding reach 到(reach 不到 → 該 metric 全 0) |
| `threshold` | `rdf:value` **數值** + `quan:unit` **單位**都精確相等才算 1.0 |
| `statistic` / `scope` / `measurement_method` / `time_window` | binding 上的 IRI 與 gold **精確相等**(`_eq`) |
| `operator` | gold operator 對應的比較函式(`quan:smaller/atMost/greater/atLeast/exactly`)是否**以 predicate 套在一個含本 metric threshold 節點的 `rdf:List`** 上(`_operator_ok`,走 `rdf:first/rest`) |

各 metric 的同維度取平均成為該維度分數。

### 2.3 case 級維度

| 維度 | 判定方式 |
|---|---|
| `tenant` | 是否有 `evsla:Tenant` 的 instance,其 `rdfs:label` 等於 gold `tenant` |
| `topology` | 同時有 `evsla:HubAndSpokeTopology` + `evsla:HubSite` instance + `evsla:SpokeSite` instance |
| `contract` | gold metric 中可從 binding reach 到的比例 |
| `precision` | 輸出 binding 中命中 gold 的比例(`matched/total`);**沒有任何 binding 時記 0,不獎勵空輸出** |

### 2.4 加權 composite

```python
WEIGHTS = {
    "metric": 2.0, "threshold": 2.0, "contract": 2.0,   # 核心:metric/門檻/契約
    "scope": 1.5, "statistic": 1.5, "precision": 1.5,
    "measurement_method": 1.0, "time_window": 1.0, "operator": 1.0,
    "tenant": 1.0, "topology": 1.0,
}
composite = Σ(WEIGHTS[k] · dims[k]) / Σ(WEIGHTS)
```

回傳 `composite`、逐維度 `dimensions`、`precision`(含 `hallucination_count`)、`errors`(逐項失配訊息,如 `threshold latency: expected 50 ms, got 60 ms`)。

> **精確-IRI 比對是刻意的**:這正是評分器的鑑別力來源 —— 詞彙對但 IRI 自創(非官方 namespace)會被歸零,所以「可 parse 的 Turtle」≠「TIO 語意正確」。GraphRAG/KGE 在 structure-only 仍拿高分,證明評分器有鑑別力而非 bug。

---

## 3. 比較報告(評分之後)

評分檔 `phase1/phase1_*.json` 之上有三個比較器,都是覆寫式產生、非歷史系統:

| 比較器 | 輸出 | 內容 |
|---|---|---|
| `compare_reports.py` | `phase1/output_quality/compare_four_way.txt` | 強配方四方:parse / coverage / triples / unknown / intent-id + Semantic Summary |
| `run_structure_experiments.write_accuracy_summary` | `phase1/output_quality/compare_structure_four_way.txt` | structure-only 四線:parse / coverage / composite / 11 維逐維度 |
| `compare_token_usage.py` | `phase1/token_usage/compare_token_usage*.txt` | prep / online / amortized token(`--variant structure` 走 structure ledger + legend) |

---

## 4. 注意事項

- `evaluate_ttl.py` 評的是 **TIO Turtle 格式 + expected element 覆蓋率 + graph-binding 語意**,不等於完整網路語意正確率。
- gold case 需含 `performance_metrics`(每項有 `ontology_term` / `threshold{value,unit}` / `statistic` / `scope` / `measurement_method` / `time_window` / `operator`)、`tenant`、`topology` 才能算語意分;缺 gold 或 parse 失敗時 `semantic=None`。
- `run_all_experiments.py --eval-only` 會覆寫固定檔名的 `phase1/phase1_*.json` 與比較報告。

## 5. 程式對照速查

| 功能 | 位置 |
|---|---|
| 外層單檔評分 | `evaluate_ttl.evaluate_file` |
| markdown fence 剝除 | `evaluate_ttl.strip_markdown_turtle_fence` |
| 參考詞表載入(cache) | `evaluate_ttl.reference_vocabulary` |
| 語意 composite | `semantic_eval.score_semantics` |
| binding 抽取(expectation-first) | `semantic_eval.extract_bindings` / `_first_obj` |
| operator over rdf:List | `semantic_eval._operator_ok` / `_list_members` |
| 維度權重 | `semantic_eval.WEIGHTS` |
