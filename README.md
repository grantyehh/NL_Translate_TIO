# CHT TIO JSON-LD Experiments

這個專案比較三條 NL -> TIO JSON-LD 生成流程：

- `LLM-only/`: 只用 LLM + few-shot。
- `GraphRag/`: GraphRAG + LLM + few-shot。
- `KGE/KGE-based-graphrag/`: GraphRAG + KGE hybrid retrieval + LLM + few-shot。

三條線共用：

- `test_cases_20.json`: 測試題目。
- `few_shot_samples.json`: few-shot JSON-LD 範例。
- `evaluate_jsonld.py`: JSON-LD 評分器。
- `compare_reports.py`: 評分報告比較器。
- `docs/standard.md`: JSON-LD 轉譯標準草案。

固定輸出位置：

- 生成結果：根目錄 `jsonld_outputs/<experiment>/*.jsonld`
- 評分結果：`phase1/phase1_*.json`
- 比較結果：`phase1/compare_three_way.txt`

## 0. 前置準備

在專案根目錄啟用環境並安裝依賴：

```bash
cd /Users/grantyeh/Grant/Project/CHT
source .venv/bin/activate
python -m pip install -r requirements.txt
```

需要設定其中一個 API key：

```bash
export GRAPHRAG_API_KEY=your_key_here
# or
export OPENAI_API_KEY=your_key_here
```

`GraphRag/` 與 `KGE/KGE-based-graphrag/` 共用同一份 GraphRAG index。TTL 變更後先用 RDF parser 產生 term-level GraphRAG input，再只在 `GraphRag/` 建一次 index：

```bash
python3 GraphRag/build_graphrag_input.py
cd /Users/grantyeh/Grant/Project/CHT/GraphRag
graphrag index --root .
```

`GraphRag/build_graphrag_input.py` 會讀取 `TM Forum Intent Ontology/*.ttl`，保留 `rdfs:comment`、`rdfs:subClassOf`、`rdfs:domain`、`rdfs:range` 等 RDF 結構，輸出到 `graphrag_term_input/`。

KGE 線會查詢上面這份共用 GraphRAG index，另外只需要自己的 KGE artifacts。如果 ontology 有變更或 artifacts 不存在，再執行：

```bash
cd /Users/grantyeh/Grant/Project/CHT/KGE/KGE-based-graphrag
python -m kge.train
```

## 1. 生成 JSON-LD

### 一鍵生成三條線

從根目錄執行：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python run_all_experiments.py
```

這會依序執行：

- `LLM-only/nl_to_tio.py`
- `GraphRag/nl_to_tio.py`
- `KGE/KGE-based-graphrag/nl_to_tio.py`

注意：`run_all_experiments.py` 預設不只生成，也會接著做評分與比較。

### 單獨生成 LLM-only

```bash
cd /Users/grantyeh/Grant/Project/CHT/LLM-only
python nl_to_tio.py
```

輸出：

```text
jsonld_outputs/llm_only/*.jsonld
```

### 單獨生成 GraphRag

```bash
cd /Users/grantyeh/Grant/Project/CHT/GraphRag
python nl_to_tio.py
```

輸出：

```text
jsonld_outputs/graphrag/*.jsonld
```

### 單獨生成 KGE hybrid

```bash
cd /Users/grantyeh/Grant/Project/CHT/KGE/KGE-based-graphrag
python nl_to_tio.py
```

輸出：

```text
jsonld_outputs/kge_hybrid/*.jsonld
```

## 2. 評分 JSON-LD

評分器是根目錄的 `evaluate_jsonld.py`。它固定讀取：

- 測資：`test_cases_20.json`
- 生成結果：`jsonld_outputs/<experiment>/*.jsonld`
- 評分輸出：`phase1/phase1_<experiment>.json`

### 一鍵重算三條線評分

如果 JSON-LD 已經生成好，只想重算評分與比較：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python run_all_experiments.py --eval-only
```

### 單獨評分 LLM-only

```bash
cd /Users/grantyeh/Grant/Project/CHT
python evaluate_jsonld.py llm_only
```

### 單獨評分 GraphRag

```bash
cd /Users/grantyeh/Grant/Project/CHT
python evaluate_jsonld.py graphrag
```

### 單獨評分 KGE hybrid

```bash
cd /Users/grantyeh/Grant/Project/CHT
python evaluate_jsonld.py kge_hybrid
```

不帶參數會一次評三條線：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python evaluate_jsonld.py
```

評分檔固定寫到：

```text
phase1/phase1_llm_only.json
phase1/phase1_graphrag.json
phase1/phase1_kge_hybrid.json
```

## 3. 比較三條線

比較器是根目錄的 `compare_reports.py`。它會一次讀取三份 `phase1_*.json` 評分報告，輸出三方平均分數、parse 成功率、覆蓋率與逐題差異。

### 一鍵產生全部比較

如果三份評分檔已經存在：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python run_all_experiments.py --eval-only
```

這會產生：

```text
phase1/compare_three_way.txt
```

### 手動比較三條線

```bash
cd /Users/grantyeh/Grant/Project/CHT
python compare_reports.py
```

## 最常用指令

完整跑一次 phase-1，也就是「生成 -> 評分 -> 比較」：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python run_all_experiments.py
```

只重算「評分 -> 比較」，不重新呼叫 LLM / GraphRAG：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python run_all_experiments.py --eval-only
```

關掉 few-shot 做 ablation：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python run_all_experiments.py --no-few-shot
```

## 注意事項

- `run_all_experiments.py` 會覆寫固定檔名的 `phase1/phase1_*.json` 與 `phase1/compare_three_way.txt`，不是歷史紀錄系統。
- `evaluate_jsonld.py` 評的是 JSON-LD 格式與 expected element 覆蓋率，不等於完整網路語意正確率。
- 如果模型輸出 Markdown code fence，evaluator 會嘗試剝掉再 parse，但理想輸出仍應該是 pure JSON-LD。
