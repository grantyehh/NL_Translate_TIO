# GraphRAG / KGE / KAG 與 LLM-only Baseline 比較計劃書

## 0. 文件目的

本計劃書定義 `GraphRag/`、`KGE/`、`KAG/` 三條 ontology-aware pipeline 與 `LLM-only/` baseline 的重新設計方向與比較協議。

目前三條 ontology-aware pipeline 在實作上都退化成「將 TTL 切 chunk 後塞進 prompt」的 dense retrieval，導致輸出與 `LLM-only/` baseline 差異很小（見 `jsonld_outputs/llm_only/TC001.jsonld` 與 `jsonld_outputs/graphrag/TC001.jsonld` 幾乎一致），失去檢驗知識增強是否有效的意義。

本文件指出：要做有效比較，`LLM-only/` 必須作為主要 baseline；GraphRAG、KGE、KAG 則必須**展現該技術的招牌機制**，並明確衡量它們相對 baseline 是提升、持平，還是因額外 context 或推理而干擾 LLM 生成。

---

## 1. 目標

1. 以 `LLM-only/` 作為「NL → TIO JSON-LD」任務的主要 baseline
2. 讓 GraphRAG、KGE、KAG 在同一任務上各自呈現獨立技術特色
3. 在同一份 test set、同一個 LLM backbone、同一套評估指標下，量化每條 ontology-aware pipeline 相對 baseline 的增益或損害
4. 產出可被討論與被引用的結論：知識增強在此任務中是否真的有幫助、在哪些題型有幫助、以及在哪些情況會混淆 LLM 生成

## 2. 共同設定（Fair Comparison Baseline）

為了讓比較結果能反映「額外知識機制」本身，而不是模型、測資或輸出格式差異，以下變數必須鎖定一致：

| 項目 | 設定 |
|---|---|
| LLM backbone | 同一個模型（建議 GPT-4 或 Claude 同層級，固定 temperature） |
| Test set | `test_cases_20.json`（20 題） |
| Ontology source | `TM Forum Intent Ontology/` 16 個 TTL 檔 |
| Output 格式 | TIO JSON-LD（符合 `docs/standard.md` 的中高粒度規範） |
| 輸出位置 | `jsonld_outputs/{graphrag,kge,kag,llm_only}/TC###.jsonld` |
| Evaluator | `evaluate_jsonld.py` + 下節定義的補充指標 |

`LLM-only/` 作為**主要 baseline** 保留，用來代表「不加入 ontology retrieval / graph reasoning / symbolic grounding，只依賴 LLM 與固定輸出規範」的表現。它不是預設下限；若 GraphRAG、KGE 或 KAG 低於 LLM-only，該結果應被視為有效 finding，表示該知識增強方法在此題型或設定下可能造成干擾。

## 3. 評估指標

每題與每條 pipeline 都需產出以下指標，匯入 `compare_reports.py`：

1. **TIO URI 使用率**：輸出中 `evsla:*` / `icm:*` / 其他 TIO namespace URI 出現的比例
2. **Schema validity**：用 SHACL / TTL `rdfs:domain` / `rdfs:range` 對輸出做結構驗證的通過率
3. **Slot accuracy**：以 `test_cases_20.json` 中的 `ontology_terms`、`performance_metrics`、`expected_tio_elements` 為 ground truth，計算 precision / recall
4. **Hallucinated URI 比例**：輸出中不在任何 TTL 內定義的 URI 比例
5. **Token cost**：每題送進 LLM 的 context token 數
6. **Baseline delta**：每條 ontology-aware pipeline 相對 LLM-only 的 per-case 分數差（例如 slot accuracy delta、schema validity delta、hallucination delta）
7. **Context interference**：額外 context 是否引入不相關 URI、錯誤 slot、或讓原本 baseline 正確的欄位變錯
8. **失敗模式分類**：人工標記（hallucinated URI / 漏 slot / 結構錯誤 / 語意錯誤 / context-induced error）

---

## 4. Pipeline A — GraphRAG

### 4.1 招牌機制

**結構化子圖檢索**：把 TTL 當成 RDF graph，從 NL 抽出的 seed entity 開始做多跳遍歷，回傳一個**子圖**（triple list + 對應 comment），而非一段 chunk 文字。

### 4.2 與舊版的差別

| 舊版 | 新版 |
|---|---|
| TTL 切 chunk 後做 cosine similarity | TTL 載入為 RDF graph，用 typed traversal |
| 回傳 top-k 段落文字 | 回傳 subgraph：`(s, p, o)` triples + 對應 `rdfs:comment` |
| LLM 自己從段落判斷哪些 URI 該用 | LLM 看到的就是 URI 與其結構關係 |

### 4.3 設計

1. **Graph build**：用 `rdflib` 把 `TM Forum Intent Ontology/` 所有 TTL 合併為一個 RDF graph
2. **三種 index**：
   - Label index：`rdfs:label` + `skos:altLabel` → URI
   - Type index：`rdf:type X` → 屬於 X 的所有 individual
   - Comment embedding index：`rdfs:comment` 文字 embedding，做語意 fallback
3. **檢索流程**：
   1. NL → 抽 seed terms（用 LLM 或 NER 都可）
   2. seed terms → 用 Label / Comment index 對到 URI
   3. 從 URI 出發做 2-hop BFS，邊類型限定為 `rdfs:subClassOf` / `rdf:type` / `rdfs:domain` / `rdfs:range` / `rdfs:subPropertyOf`
   4. 子圖序列化為 triple list 餵給 LLM
4. **Prompt**：LLM 被告知「以下是與此 intent 相關的 TIO 子圖，請使用其中的 URI 生成 JSON-LD」

### 4.4 驗證的假設

「結構化關係子圖」比「文字段落」更能讓 LLM 對齊到正確的 URI 與層級。

### 4.5 招牌指標

預期在 **TIO URI 使用率** 與 **Schema validity** 上勝出（因為 LLM 直接看到合法 URI 與其鄰居）。
弱項可能在 **Token cost**（子圖可能展開得比 chunk 大）。

---

## 5. Pipeline B — KGE

### 5.1 招牌機制

**Embedding-based retrieval + link prediction**：把 TTL 三元組訓成 entity & relation embedding。檢索不只是相似度，還能**預測該補上但 NL 沒提到的關聯**。

### 5.2 與舊版的差別

| 舊版 | 新版 |
|---|---|
| TTL chunk 做 sentence embedding（其實是 dense retrieval，不是 KGE） | TTL triples 訓 TransE / RotatE / ComplEx |
| Top-k chunk | Top-k URI + **預測的 likely triples** |
| 沒有任何補全行為 | NL 沒提到的關聯由 link prediction 補出 |

### 5.3 設計

1. **Triple extraction**：把 TTL parse 成 `(head, relation, tail)` triple list
2. **Embedding training**：用 PyKEEN 訓 TransE 或 RotatE
   - 即使 graph 小，做 demo 規模夠
   - 訓練時負樣本可結合 `rdfs:domain` / `rdfs:range` 反推非法組合
3. **檢索流程**：
   1. NL 抽 mention → 用 LM encoder 編碼 → 跟 entity embedding 做相似度，找出 top-k URI
   2. **Link prediction**：對每個 grounded entity，預測 (entity, ?, ?) 中得分最高的 relation+tail
   3. 餵給 LLM 的是：**[grounded URIs] + [predicted likely triples]**
4. **Prompt**：LLM 被告知「以下 URI 與 NL 相關，且依結構推測這些 triples 也應出現」

### 5.4 驗證的假設

KGE 能從**結構規律**補出 NL 沒明說但 schema 要求的關聯（例：用了 `SlaExpectation` 就應該有 `hasMetric` 與 `hasThreshold`）。

### 5.5 招牌指標

預期在 **Slot recall** 上勝出（補全能力是招牌）。
弱項可能在 **實作複雜度**（要訓 embedding model）與 **小 graph 的 embedding 質量**。

---

## 6. Pipeline C — KAG

### 6.1 招牌機制

**Logical-form-first + schema-strict reasoning**：NL → logical form (slot frame) → 每個 slot 用 symbolic mapping 對到 TTL URI → schema 驗證 → 模板渲染。LLM 只負責 NL 解析，URI 對映與結構生成由 symbolic 部分掌控。

### 6.2 與舊版的差別

| 舊版 | 新版 |
|---|---|
| 直接 NL → JSON-LD | NL → logical form → grounded slots → JSON-LD |
| LLM 自由生成 URI | URI 由 deterministic mapping table 決定 |
| 沒有 schema enforcement | SHACL / TTL constraint 強制驗證，違反就 reject 重生 |

### 6.3 設計

1. **Logical form schema**：直接沿用 `test_cases_20.json` 結構

   ```json
   {
     "intent_type": "...",
     "tenant": "...",
     "service_target": "...",
     "topology": {"hub": "...", "spokes": ["..."]},
     "expectations": [
       {
         "type": "...",
         "metric": "...",
         "op": "...",
         "threshold": {"value": 0, "unit": "..."},
         "statistic": "...",
         "scope": "...",
         "method": "...",
         "window": "..."
       }
     ]
   }
   ```

2. **Step 1 — NL → logical form**：LLM 只負責解析自然語言成上述 slot frame，**明確禁止生成 URI**
3. **Step 2 — slot grounding**：每個 slot value 走 deterministic mapping table
   - mapping table 從 TTL 派生（`rdfs:label` / `skos:altLabel` → URI）
   - 找不到對應的 slot 標記為 unresolved，進入 fallback
4. **Step 3 — schema validation**：用 SHACL 或 TTL `rdfs:domain` / `rdfs:range` 驗證 grounded triples，違反就回到 Step 1 重生（最多 N 次）
5. **Step 4 — template render**：Jinja template 把 grounded slots 渲染成 JSON-LD

### 6.4 驗證的假設

「先把 NL 結構化、再對齊 schema、再渲染」比「讓 LLM 自由生成 JSON-LD」更穩定、URI 更精準。

### 6.5 招牌指標

預期在 **Schema validity** 與 **Hallucinated URI** 上勝出（因為 URI 不是生成出來的）。
弱項可能在 **對 NL 變異的 robust 度**（slot extractor 對未見過的表述容易失敗）。

---

## 7. 預期比較結論（待實驗驗證）

| 維度 | LLM-only baseline | GraphRAG | KGE | KAG |
|---|---|---|---|---|
| URI 精準度 | 中-高（取決於 prompt 與 few-shot） | 中 | 中-高 | **高** |
| 補全能力 | 中 | 低 | **高** | 中 |
| Schema 合規 | 中-高 | 中 | 中 | **高** |
| Context interference 風險 | **低** | 中 | 高 | 中 |
| Token cost | **低** | 高 | 低-中 | 中 |
| NL 變異 robust 度 | 中-高 | 中 | 中-高 | 低 |
| 實作複雜度 | **低** | 中 | 高 | 高 |

這份預期表格的作用，是讓實驗結果有「對照基準」。若 GraphRAG、KGE 或 KAG 勝過 LLM-only，代表其知識機制對該任務有實際增益；若持平或輸給 LLM-only，則代表額外 ontology context、graph traversal、link prediction 或 symbolic grounding 可能沒有提供足夠訊號，甚至干擾 LLM 原本的生成能力。

---

## 8. 實施順序

依「技術差異展示效益 ÷ 實作成本」排序：

1. **Pipeline A (GraphRAG) 重構**：rdflib + typed traversal，1–2 天可完成雛形
2. **Pipeline C (KAG) 重構**：寫 logical-form prompt + mapping table + SHACL 驗證，2–3 天
3. **Pipeline B (KGE) 重構**：PyKEEN 訓 embedding + link prediction 整合，3–5 天
4. **評估指標補齊**：擴充 `evaluate_jsonld.py`，加入 URI 使用率、hallucination、token cost、baseline delta、context interference 指標
5. **跑全量比較**：四條 pipeline × 20 題，並以 LLM-only 為 baseline 匯總到 `compare_reports.py`
6. **撰寫實驗結果與分析**

---

## 9. 範圍以外（不在本計劃內）

- 不擴充 ontology（只用現有 `TM Forum Intent Ontology/`）
- 不擴大 test set（先把 20 題做穩）
- 不追求 SOTA（目的是技術比較，不是刷分）
- 不做三技術融合的 pipeline（融合是另一個議題，與本比較目標衝突）
