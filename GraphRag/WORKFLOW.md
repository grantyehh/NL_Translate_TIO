# GraphRag TIO 專案流程說明

本文件統整目前 NL → TIO Turtle 生成與離線評測的流程，方便後續繼續開發。

---

## 1. 目標

將自然語言意圖（NL）轉換為 **TM Forum Intent Ontology (TIO) v3.6.0** 的 **Turtle (RDF)**，並以腳本檢查語法、詞彙與測資預期元素。

推理時**不**將評分規則或「標準答案結構」餵給模型；改以 **`few_shot_samples.json`** 示範輸出格式與官方 CURIE 用法。

---

## 2. 主要檔案與角色

| 項目 | 作用 |
|------|------|
| `../test_cases_20.json` | 根目錄共用測資；每題 `id`、`nl_intent`、`expected_tio_elements` 等；供生成迴圈與 **evaluate_ttl.py** 離線檢查。**不**含 rubric。 |
| `few_shot_samples.json` | 與測資**不同情境**的 NL + Turtle 範例；**僅**由 `nl_to_tio.py` 讀入並組進 prompt。 |
| `nl_to_tio.py` | 對每題：GraphRAG 查上下文 → 呼叫 LLM → 寫入 `tio_outputs/<id>.ttl`。 |
| `TM Forum Intent Ontology/*.ttl` | 官方本體檔，作為詞彙與型別的 ground truth。 |
| `evaluate_ttl.py` | 解析 `tio_outputs/*.ttl`，對照本體與 `expected_tio_elements`。**已移除 rubric 評測**。 |
| `report.json`（可選） | 執行 `evaluate_ttl.py --json-out report.json` 產生的完整 JSON 報告。 |

---

## 3. 生成流程（`nl_to_tio.py`）

1. 預設讀取根目錄 `../test_cases_20.json`，逐題處理。
2. （預設）讀取 `few_shot_samples.json`，將範例組進 **user message**（提示僅學結構與前綴，勿抄寫範例內容）。
3. 以 **GraphRAG** `local` 模式查詢，取得與該 NL 相關的 TIO 脈絡文字。
4. 呼叫 **OpenAI**（需環境變數 `OPENAI_API_KEY` 或 `GRAPHRAG_API_KEY`），依 system + user 產生**純 Turtle**（不含 markdown code fence）。
5. 寫入 `tio_outputs/<TCxxx>.ttl`。

### 常用參數

- `--few-shot`：few-shot JSON 路徑（預設 `few_shot_samples.json`）
- `--no-few-shot`：不使用 few-shot 檔
- `--test-cases`：測資路徑（預設 `../test_cases_20.json`）

---

## 4. 評測流程（`evaluate_ttl.py`）

1. 從 `TM Forum Intent Ontology` 載入參考詞彙（classes、properties，含 `fun:Function` 作為 predicate）。
2. 依共用測資中的每個 `id`，讀取 `tio_outputs/<id>.ttl`（若缺檔則標為錯誤）。
3. 檢查項目包含：
   - Turtle **語法**（rdflib 解析；若內容含 \`\`\` 會先剝除 fence）
   - **前綴**是否與官方 namespace 一致
   - 是否出現本體**未定義**的 predicate 或 `rdf:type` 物件
   - **`expected_tio_elements`**：若為 class 則需有對應 `rdf:type` 實例；若為 property/function 則需至少出現為 predicate
   - 實例 URI 是否**包含 case id**（`intent_uri_contains_case_id`）

**注意**：已**不**執行舊版 rubric（required_patterns / forbidden 等）評測。

---

## 5. 資料與「洩題」界線

| 資料 | 是否進入 LLM prompt |
|------|---------------------|
| `few_shot_samples.json` | 是（格式示範；情境與測資不同） |
| GraphRAG 查詢結果 | 是 |
| 當題 `nl_intent` | 是 |
| `expected_tio_elements` | **否**（僅 `evaluate_ttl.py` 使用） |

若希望測資檔完全不含評分用欄位，可再將 `expected_tio_elements` 拆到獨立檔（例如僅評分腳本讀取），與純題目檔分離。

---

## 6. 常用指令

```bash
# 產生 Turtle（於專案根目錄執行）
python3 nl_to_tio.py

# 評測（終端摘要）
python3 evaluate_ttl.py

# 評測並寫出 JSON 報告
python3 evaluate_ttl.py --json-out report.json
```

---

## 7. 環境需求摘要

- Python 與依賴：`rdflib`（evaluate）、`openai`、`python-dotenv`（nl_to_tio）
- GraphRAG CLI：`graphrag` 需在 PATH，且專案已初始化可查詢
- API：`OPENAI_API_KEY` 或 `GRAPHRAG_API_KEY`（見 `nl_to_tio.py`）

---

*本文件依目前程式行為整理；若之後改動腳本或檔名，請同步更新此檔。*
