# CHT TIO GraphRAG Experiments

這個專案有三條主要實驗線：

- `LLM-only/`: 不使用 GraphRAG、不使用 KGE，直接用 LLM + few-shot 把自然語言轉成 TIO Turtle。
- `GraphRag/`: baseline，使用 GraphRAG + LLM + few-shot，把自然語言轉成 TIO Turtle。
- `KGE/KGE-based-graphrag/`: 在 baseline 上額外注入 KGE hybrid retrieval term hints。

三條線現在都使用相同的：

- `test_cases_20.json`
- `few_shot_samples.json`
- `evaluate_ttl.py` 評估口徑
- `graphrag_input/`（加工後的 GraphRAG 文字化輸入）
- `TM Forum Intent Ontology/`（原始 TIO ontology 檔）

目前唯一設計上的主要差別是：`KGE` 版會多注入 `kge_context`。

依賴現在統一收斂在根目錄 `requirements.txt`，`GraphRag/` 與 `KGE/KGE-based-graphrag/` 共用同一份安裝清單。

## 1. 先決條件

### 1.1 Python

建議使用 Python 3.11+。

### 1.2 建議使用虛擬環境

建議使用專案自己的虛擬環境，不要直接安裝到系統 Python。原因是這個專案同時需要：

- `graphrag`
- `openai`
- `rdflib`
- `python-dotenv`
- `numpy`
- `torch`
- `pykeen`

這些套件的依賴鏈較重，直接裝到系統環境很容易造成版本污染，影響實驗可重現性。

建議在專案根目錄建立一個 `.venv`：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python -m venv .venv
```

啟用方式：

```bash
source .venv/bin/activate
```

之後 README 裡的 `python`、`graphrag` 指令，都預設在這個虛擬環境內執行。

### 1.3 GraphRAG CLI

本專案需要本機可執行的 `graphrag` CLI。

可先確認：

```bash
graphrag --help
```

如果你打算把 `graphrag` 也裝進同一個虛擬環境，請先啟用 `.venv` 再安裝。

### 1.4 OpenAI / GraphRAG API Key

`nl_to_tio.py` 會讀取下列其中一個環境變數：

- `GRAPHRAG_API_KEY`
- `OPENAI_API_KEY`

你可以直接在各子專案目錄放 `.env`，例如：

```env
GRAPHRAG_API_KEY=your_key_here
```

## 2. 安裝依賴

以下安裝步驟都假設你已經先啟用虛擬環境：

```bash
cd /Users/grantyeh/Grant/Project/CHT
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 2.1 共用依賴

兩條實驗線共用根目錄的 `requirements.txt`：

```bash
python -m pip install -r requirements.txt
```

目前統一安裝的套件包含：

- `graphrag`
- `openai`
- `python-dotenv`
- `rdflib`
- `numpy`
- `torch`
- `pykeen`

## 3. 手動執行整體流程

### 3.1 LLM-only

1. 進入實驗目錄：

```bash
cd LLM-only
```

2. 生成 Turtle：

```bash
python nl_to_tio.py
```

可選參數：

```bash
python nl_to_tio.py --no-few-shot
python nl_to_tio.py --few-shot ../few_shot_samples.json
python nl_to_tio.py --test-cases ../test_cases_20.json
```

3. 用根目錄共用 evaluator 評估輸出：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python evaluate_ttl.py \
  --outputs-dir LLM-only/tio_outputs \
  --json-out phase1/phase1_llm_only.json
```

輸出重點：

- 生成的 Turtle 在 `LLM-only/tio_outputs/`
- phase-1 評估報告寫到 `phase1/phase1_llm_only.json`

### 3.2 Baseline: GraphRag

1. 進入實驗目錄：

```bash
cd GraphRag
```

2. 如果你只要重跑生成與評估，而且目錄內已有 `output/`，可以直接跳過重建索引。

3. 如果你要重建 GraphRAG index：

```bash
graphrag index --root .
```

4. 生成 Turtle：

```bash
python nl_to_tio.py
```

可選參數：

```bash
python nl_to_tio.py --no-few-shot
python nl_to_tio.py --few-shot ../few_shot_samples.json
python nl_to_tio.py --test-cases ../test_cases_20.json
```

5. 用根目錄共用 evaluator 評估輸出：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python evaluate_ttl.py \
  --outputs-dir GraphRag/tio_outputs \
  --json-out phase1/phase1_graphrag.json
```

輸出重點：

- 生成的 Turtle 在 `GraphRag/tio_outputs/`
- phase-1 評估報告寫到 `phase1/phase1_graphrag.json`

### 3.3 KGE Hybrid

1. 進入實驗目錄：

```bash
cd KGE/KGE-based-graphrag
```

2. 如果你只要重跑生成與評估，而且目錄內已有 `output/`，可以直接跳過重建 GraphRAG index。

3. 如果你要重建 GraphRAG index：

```bash
graphrag index --root .
```

4. 如果你要重建 KGE artifacts，先訓練 KGE 與 text embeddings：

```bash
python -m kge.train
```

完成後會產生：

- `kge_data/triples.tsv`
- `kge_data/entity_ids.json`
- `kge_data/entity_kge_embeddings.npy`
- `kge_data/entity_text_embeddings.npy`
- `kge_data/manifest.json`

如果 `GRAPHRAG_API_KEY` 或 `OPENAI_API_KEY` 沒有設定，`kge.train` 仍可產生結構 embedding，但不會產生 text embeddings，這時 hybrid retrieval 會不完整。

5. 生成 Turtle：

```bash
python nl_to_tio.py
```

可選參數：

```bash
python nl_to_tio.py --no-few-shot
python nl_to_tio.py --few-shot ../../few_shot_samples.json
python nl_to_tio.py --test-cases ../../test_cases_20.json
```

6. 用根目錄共用 evaluator 評估輸出：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python evaluate_ttl.py \
  --outputs-dir KGE/KGE-based-graphrag/tio_outputs \
  --json-out phase1/phase1_kge_hybrid.json
```

輸出重點：

- 生成的 Turtle 在 `KGE/KGE-based-graphrag/tio_outputs/`
- phase-1 評估報告寫到 `phase1/phase1_kge_hybrid.json`

## 4. 從根目錄執行的最短命令集

如果你在專案根目錄 `/Users/grantyeh/Grant/Project/CHT`，可直接這樣跑。

### 4.1 建議的四種用法

平常只需要記這四種情境。

1. 快速檢查：重新生成三條線，跑 phase-1

```bash
cd /Users/grantyeh/Grant/Project/CHT
python run_all_experiments.py
```

預設會使用根目錄的 `test_cases_20.json`，並重新執行：

- `LLM-only/nl_to_tio.py`
- `GraphRag/nl_to_tio.py`
- `KGE/KGE-based-graphrag/nl_to_tio.py`
- 根目錄共用的 `evaluate_ttl.py`

輸出會寫到 `phase1/`。

2. 正式完整實驗：重新生成三條線，phase-1 與 phase-2 都跑

```bash
cd /Users/grantyeh/Grant/Project/CHT
python run_all_experiments.py --phase all
```

3. Few-shot ablation：重新生成三條線，但整批關掉 few-shot

```bash
cd /Users/grantyeh/Grant/Project/CHT
python run_all_experiments.py --phase all --no-few-shot
```

4. 只重算評估：不重新 query / generation，只重算指定 phase

```bash
cd /Users/grantyeh/Grant/Project/CHT
python run_all_experiments.py --phase phase2 --eval-only
```

`--eval-only` 適合以下情況：

- 你改了 `evaluate_ttl.py`
- 你改了 `evaluate_ttl_phase2.py`
- 你改了 `goldens/`
- 你只想重算報告，不想再次呼叫 LLM 或 GraphRAG

如果你想改用另一份測資檔：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python run_all_experiments.py --test-cases /path/to/custom_test_cases.json
```

如果你想指定評估階段：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python run_all_experiments.py --phase phase1
python run_all_experiments.py --phase phase2
python run_all_experiments.py --phase all
```

說明：

- `phase1`: 跑 `evaluate_ttl.py`，輸出寫到 `phase1/`，並產生 pairwise compare 與 `phase1/phase1_summary.txt`
- `phase2`: 跑 `evaluate_ttl_phase2.py`，輸出寫到 `phase2/`，並產生 `phase2/phase2_summary.txt`
- `all`: phase1 與 phase2 都跑
- `--no-few-shot`: 只建議用在 ablation
- `--eval-only`: 跳過 `nl_to_tio.py`，只重算評估報告

`--test-cases` 會同步傳給三條實驗線的 `nl_to_tio.py`、根目錄共用的 `evaluate_ttl.py`，以及最後的 `compare_reports.py`。

phase1 輸出會寫到 `phase1/`，包含：

- `phase1_llm_only.json`
- `phase1_graphrag.json`
- `phase1_kge_hybrid.json`
- `compare_llm_only_vs_graphrag.txt`
- `compare_graphrag_vs_kge_hybrid.txt`
- `compare_llm_only_vs_kge_hybrid.txt`
- `phase1_summary.txt`

### 4.2 跑 LLM-only

```bash
cd /Users/grantyeh/Grant/Project/CHT/LLM-only
python nl_to_tio.py
cd /Users/grantyeh/Grant/Project/CHT
python evaluate_ttl.py --outputs-dir LLM-only/tio_outputs --json-out phase1/phase1_llm_only.json
```

### 4.3 跑 GraphRag baseline

```bash
cd /Users/grantyeh/Grant/Project/CHT/GraphRag
python nl_to_tio.py
cd /Users/grantyeh/Grant/Project/CHT
python evaluate_ttl.py --outputs-dir GraphRag/tio_outputs --json-out phase1/phase1_graphrag.json
```

### 4.4 跑 KGE hybrid

```bash
cd /Users/grantyeh/Grant/Project/CHT/KGE/KGE-based-graphrag
python -m kge.train
python nl_to_tio.py
cd /Users/grantyeh/Grant/Project/CHT
python evaluate_ttl.py --outputs-dir KGE/KGE-based-graphrag/tio_outputs --json-out phase1/phase1_kge_hybrid.json
```

### 4.5 在根目錄比較兩份報告

```bash
cd /Users/grantyeh/Grant/Project/CHT
python compare_reports.py \
  --base phase1/phase1_graphrag.json \
  --target phase1/phase1_kge_hybrid.json \
  --base-name GraphRag \
  --target-name KGE-hybrid \
  --test-cases test_cases_20.json
```

```bash
cd /Users/grantyeh/Grant/Project/CHT
python compare_reports.py \
  --base phase1/phase1_llm_only.json \
  --target phase1/phase1_graphrag.json \
  --base-name LLM-only \
  --target-name GraphRag \
  --test-cases test_cases_20.json \
  --out phase1/compare_llm_only_vs_graphrag.txt
```

如果你希望同時把比較結果存成文字檔，可以加上 `--out`：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python compare_reports.py \
  --base phase1/phase1_graphrag.json \
  --target phase1/phase1_kge_hybrid.json \
  --base-name GraphRag \
  --target-name KGE-hybrid \
  --test-cases test_cases_20.json \
  --out phase1/compare_graphrag_vs_kge_hybrid.txt
```

### 4.6 跑 phase-2 evaluator

如果你想加入 `goldens/` 的結構檢查，可以使用根目錄的 `evaluate_ttl_phase2.py`：

```bash
cd /Users/grantyeh/Grant/Project/CHT
python evaluate_ttl_phase2.py \
  --outputs-dir GraphRag/tio_outputs \
  --json-out phase2/phase2_graphrag.json
```

預設會使用：

- `test_cases_20.json`
- `goldens/golden_cases.json`
- `TM Forum Intent Ontology`
- `graphrag_input`

目前 phase-2 會自動檢查：

- `expected_tio_elements`
- `must_have_triples`
- `must_not_have_predicates`
- `expected_values`（第一版 heuristic，自動檢查數值、單位、比較方向與關鍵字錨點）

## 5. 各檔案角色

- `LLM-only/nl_to_tio.py`: LLM-only baseline 生成器
- `few_shot_samples.json`: 三條實驗線共用的 few-shot 範例
- `evaluate_ttl.py`: 根目錄共用的 phase-1 evaluator
- `phase1/`: phase-1 JSON 報告、compare 文字檔與 `phase1_summary.txt`
- `GraphRag/nl_to_tio.py`: baseline 生成器
- `graphrag_input/`: GraphRAG 與 KGE-baseline 共用的文字化 ontology 輸入
- `test_cases_20.json`: 三條實驗線共用的 20 題測資
- `KGE/KGE-based-graphrag/nl_to_tio.py`: KGE-hybrid 生成器
- `KGE/KGE-based-graphrag/kge/train.py`: 產生 KGE 與 text embedding artifacts
- `KGE/KGE-based-graphrag/kge/retrieve.py`: 注入 KGE hybrid retrieval term hints
- `compare_reports.py`: 比較任兩份 phase-1 報告
- `evaluate_ttl_phase2.py`: 吃 `goldens/` 的 phase-2 evaluator
- `phase2/`: phase-2 JSON 報告與 `phase2_summary.txt`
- `goldens/`: 人工標準答案與 golden metadata
- `run_all_experiments.py`: 一鍵重跑三條線並產出比較報告

## 6. 常見注意事項

- `graphrag query` 依賴已存在的 `output/` index，沒有 index 時 `nl_to_tio.py` 會失敗。
- `evaluate_ttl.py` 評的是語法、官方詞彙一致性、`expected_tio_elements` 覆蓋率，不是完整語意正確率。
- 即使 Turtle 可 parse，也可能因為用了不在官方 ontology 裡的 predicate 或 type，而在 evaluator 裡被記為 `unknown_predicates` 或 `unknown_types`。
- 若模型輸出 markdown code fence，evaluator 會嘗試剝掉 fence 後再 parse，但這代表輸出本身仍不算乾淨的 pure Turtle。

## 7. 建議的手動實驗順序

如果你要做一次公平比較，建議照這個順序：

1. 在 `LLM-only/` 重跑 `nl_to_tio.py`
2. 在 `GraphRag/` 重跑 `nl_to_tio.py`
3. 在 `KGE/KGE-based-graphrag/` 先跑 `python -m kge.train`
4. 在 `KGE/KGE-based-graphrag/` 重跑 `nl_to_tio.py`
5. 回到根目錄用共用 `evaluate_ttl.py` 產出 `phase1/` JSON
6. 如需結構化 golden 評估，再跑 `evaluate_ttl_phase2.py` 產出 `phase2/` JSON
7. 再用 `python compare_reports.py` 或 `python run_all_experiments.py` 彙整結果

這樣可以確保三條線共享同一套測資、few-shot 與 evaluator，並清楚比較：

- `LLM-only`
- `GraphRAG + LLM`
- `GraphRAG + KGE + LLM`
