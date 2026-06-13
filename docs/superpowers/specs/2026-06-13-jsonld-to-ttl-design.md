# JSON-LD → Turtle 輸出格式遷移設計

**日期:** 2026-06-13
**分支:** `codex/jsonld-to-ttl`(基於 `codex/jsonld-snapshot-20260613`)
**目標:** 把目前成熟的 EVSLA hub-and-spoke 實驗線,輸出格式從 API-friendly JSON-LD 改回 TIO Turtle,**保留全部既有方法邏輯**,**完全不動 `tio-agent/`**。

---

## 1. 背景與決策

### 1.1 為何走「改新版輸出」而非「還原舊版」

repo 有兩條線:

- **舊線(`main` → `codex/ttl-kag`):** 早期實驗,輸出 Turtle,情境為**通用 `icm:` intent**。方法邏輯停留在舊版。
- **新線(`new-methods` → `codex/jsonld-snapshot-20260613`):** 累積 20+ commit 的成熟成果 —— GraphRAG 改為 rdflib 2-hop typed traversal、KGE link prediction、KAG resume/contract fallback、EVSLA grounding suite、token usage 評估;情境改為 **EVSLA hub-and-spoke**,輸出 JSON-LD。

整個計畫目標是「輸出格式回到 Turtle」。若從舊線還原(方案 A),須手動重補新線那 20+ commit 的方法邏輯,工多且易與原版產生細微差異。改採**方案 B**:從新線開分支,只替換「序列化層」。理由:方法邏輯是高價值難做的部分(已完成),格式是又薄又集中的一層。

### 1.2 兩線 few-shot / test case 不相容(關鍵)

- 舊線 few-shot(6 例)是通用 `icm:` 範例,**不可沿用**。
- 新線 few-shot(4 例)與 test_cases(20 題,全 `Hub-Spoke SLA`)都是 EVSLA hub-and-spoke。
- 因此 few-shot 的 Turtle 要**依新線那 4 個 hub-and-spoke 範例手寫**,不是搬舊線內容。

---

## 2. 範圍

### 2.1 納入
- `evsla_prompt.py`(輸出契約核心)
- 四條線 `nl_to_tio.py`:`LLM-only/`、`GraphRag/`、`KGE/KGE-based-graphrag/`、`KAG/`
- `few_shot_samples.json`
- 評估器:`evaluate_jsonld.py` → `evaluate_ttl.py`
- `run_all_experiments.py`
- 各 `test_nl_to_tio.py` 及相關測試(`test_evaluate_*`、`test_token_usage` 等)
- 輸出目錄:`jsonld_outputs/` → `tio_outputs/`

### 2.2 明確排除(本次不碰)
- `tio-agent/`(TS 寫的 hub-and-spoke validator,維持讀 JSON-LD)
- `mechanism.md` / `mechanism_deck.pptx` 等說明素材(除非提到輸出格式才順手更新)
- `kge_hybrid` 這個 legacy 輸出目錄(不在 runner 內,維持現狀)

---

## 3. 架構與資料流

### 3.1 現況(JSON-LD)
```
nl_intent + tc_id
   │
   ├─ build_evsla_system_prompt(tc_id, retrieval_mode)   ← evsla_prompt.py(集中定義 JSON-LD 契約)
   │    └ @context / ontologyType / tenant / expectationTarget(evsla: predicates)/ 對應規則
   ├─ few-shot block(讀 few_shot_samples.json 的 `jsonld` 欄位)
   ├─ (各方法的 retrieval context:graphrag / kge / kag)
   │
   ▼ LLM 產生 JSON-LD 文字
   └─ 寫到 jsonld_outputs/<method>/<TC>.jsonld
        ▼
   evaluate_jsonld.py(契約檢查 + expected_tio_elements 覆蓋)→ phase1/phase1_<method>.json
```

### 3.2 目標(Turtle)
```
nl_intent + tc_id
   │
   ├─ build_evsla_system_prompt(...)  ← 改寫:指示輸出 TIO Turtle(@prefix icm:/evsla:/quan:)
   │    └ 對應規則不變(latency→evsla:latency…),但落到 Turtle predicate 寫法
   ├─ few-shot block(讀 `turtle` 欄位)
   ├─ (retrieval context 不變)
   │
   ▼ LLM 產生 Turtle 文字
   └─ 寫到 tio_outputs/<method>/<TC>.ttl
        ▼
   evaluate_ttl.py(rdflib parse + expected_tio_elements 覆蓋 + reference ontology 比對)
        → phase1/phase1_<method>.json
```

**核心洞察:** 輸出契約集中在 `evsla_prompt.py`,故格式改寫主要落在這一支;各 `nl_to_tio.py` 主要只改「輸出路徑/副檔名」與「few-shot 讀 `turtle` 欄位」。

---

## 4. 各元件變更

### 4.1 `evsla_prompt.py`(最大改寫)
- `build_evsla_system_prompt()` 從「You generate API-friendly TIO JSON-LD …」改為「You generate TIO Turtle …」。
- 移除 `@context` / `@type` / API-friendly 欄位名指示,改為 Turtle 骨架:`@prefix` 宣告、`ex:` instance 前綴、icm: 結構(Intent → Expectation → Target → valuesOfTargetProperty)、evsla: 與 quan: 用法。
- **保留** metric 對應表(latency→evsla:latency/LESS_THAN/evsla:twamp、packet_loss→evsla:packetLoss、95%→evsla:p95、所有分點→evsla:hubToAllSpokes…),只改成 Turtle 三元組呈現。

### 4.2 四條線 `nl_to_tio.py`
- `output_path_for_case`:`jsonld_outputs/<m>/<TC>.jsonld` → `tio_outputs/<m>/<TC>.ttl`。
- few-shot block 讀 `turtle` 欄位(原讀 `jsonld`)。
- 函式/變數命名(如 `generate_jsonld_code`)改回 turtle 語意;移除 JSON fence 處理,改 Turtle fence。
- KAG:`solver/tio_jsonld_generator.py` → turtle generator,移植 `codex/ttl-kag:KAG/example_project/solver/tio_turtle_generator.py` 並接上 EVSLA solver context。
- 各方法 retrieval 邏輯**不變**。

### 4.3 `few_shot_samples.json`
- 保留 4 例的 `pattern`/`nl_intent`,新增 `turtle` 欄位(手寫,移除 `jsonld` 欄位)。
- Turtle 內容須對應原 jsonld 語意,使用 icm:(真實 predicate,非 API-friendly 名)+ evsla: + quan:。
- icm: predicate 真實名稱來源:`TM Forum Intent Ontology/` 參考本體 + `codex/ttl-kag` 舊 turtle few-shot 的 icm: 慣用寫法。
- 更新 `description` 為 turtle 版說明。

### 4.4 評估器
- 移植 `codex/ttl-kag:evaluate_ttl.py`,取代 `evaluate_jsonld.py`。
- 兩版吃同一份 `expected_tio_elements`(`icm:` CURIE),核心可直接用。
- **必做確認:** reference ontology 載入須納入 `TM Forum Intent Ontology/EnterpriseVpnSlaOntology.ttl`,使 evsla: 詞彙不被判為未知。
- 報告 JSON 維持既有 key(`parse_ok`、`expected_coverage_ratio` 等)以相容既有比較腳本。

### 4.5 `run_all_experiments.py`
- `PHASE1_EVALUATOR = evaluate_ttl.py`。
- 四方法(llm_only / graphrag / kge / kag)輸出/評估路徑改 `tio_outputs` + `.ttl`。

### 4.6 測試
- 各 `test_nl_to_tio.py`:斷言從 JSON-LD 契約改為 Turtle 契約(輸出 `.ttl`、prompt 提到 Turtle、KAG 用 turtle generator、不得殘留 `tio_jsonld_generator`)。
- `test_evaluate_*` / `test_token_usage` / `test_compare_*`:改吃 ttl 路徑與評估器。

---

## 5. 用到的 Ontology(已驗證)

新線 few-shot/test case 僅用 **3 個**:

| Ontology | 用途 | 代表詞彙 |
|---|---|---|
| `icm` Intent Common Model | 核心結構 | Intent、PropertyExpectation、Context、Service、(真實 predicate)hasExpectation/Target/valuesOfTargetProperty… |
| `evsla` EnterpriseVpnSla | hub-spoke / SLA | Tenant、hasHub/HubSite、hasSpoke/SpokeSite、HubAndSpokeTopology、hasMetric/Threshold/Statistic/Scope、p95/p99、hubToAllSpokes/specificSpoke、twamp… |
| `quan` QuantityOntology | 數值 | quan:Quantity(value+unit) |

**不會**用到 log:/set:/met:/math:/ig: 等其他本體。

---

## 6. 驗收標準

1. 四條線單元測試全綠,且斷言已改為 Turtle 契約。
2. 四條線各能產出 `tio_outputs/<method>/TC*.ttl`,rdflib 可成功 parse。
3. `evaluate_ttl.py` 對 20 題 hub-spoke 輸出能計算 `expected_tio_elements` 覆蓋,evsla: 詞彙不被判未知。
4. `run_all_experiments.py` 端到端可跑完並寫出 `phase1/phase1_<method>.json`。
5. 全 repo(排除 `tio-agent/`)無殘留會誤導的 JSON-LD 輸出路徑/契約。
6. `tio-agent/` 未被修改。

---

## 7. 風險與處置

- **手寫 few-shot 語意偏差:** 4 例逐一對照原 jsonld 的 evsla: 述詞與 scope/hub/spoke 結構;完成後用 rdflib parse 驗證可解析。
- **evaluate_ttl 對 evsla: 視為未知詞彙:** 載入 reference ontology 時納入 EnterpriseVpnSlaOntology.ttl;以一題實跑驗證覆蓋計算正確。
- **API-friendly 名 → 真實 icm: predicate 對應錯誤:** 以 `TM Forum Intent Ontology/` 本體為準,並參考舊 turtle few-shot 既有寫法。
- **KAG turtle generator 與 EVSLA solver context 接點:** 移植後以 KAG 單元測試 + 一題實跑確認 delegation 正常。
