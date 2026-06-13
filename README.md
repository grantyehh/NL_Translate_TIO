# CHT TIO Turtle Experiments

這個專案比較**四條** NL -> TIO Turtle 生成流程：

- `LLM-only/`: 只用 LLM + few-shot。
- `GraphRag/`: GraphRAG + LLM + few-shot。
- `KGE/KGE-based-graphrag/`: KGE text grounding + TransE link prediction + LLM + few-shot。
- `KAG/`: OpenSPG/KAG kg-builder + 5-way solver retrieval(atomic_query / outline / summary / vector / table)+ LLM + few-shot。後端走 Docker stack(server + Neo4j + MySQL + MinIO)。詳見 [`KAG/example_project/README.md`](KAG/example_project/README.md)。

四條線共用：

- `test_cases_20.json`: 測試題目。
- `few_shot_samples.json`: few-shot TIO Turtle 範例(`turtle` 欄位)。
- `evsla_prompt.py`: 共用 EVSLA system prompt 組裝。
- `evaluate_ttl.py`: TIO Turtle 評分器。
- `compare_reports.py`: 評分報告比較器。
- `docs/standard.md`: TIO 轉譯標準草案。

固定輸出位置:

- 生成結果:根目錄 `tio_outputs/<experiment>/*.ttl`(`<experiment>` ∈ `llm_only / graphrag / kge / kag`)
- 評分結果:`phase1/phase1_*.json`
- 比較結果:`phase1/compare_four_way.txt`(舊版 3-way 的 `compare_three_way.txt` 保留作為歷史對照)

## 0. 前置準備

### 0.1 LLM-only / GraphRag / KGE 共用環境

在專案根目錄啟用環境並安裝依賴:

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
source .venv/bin/activate
python -m pip install -r requirements.txt
```

需要設定其中一個 API key:

```bash
export GRAPHRAG_API_KEY=your_key_here
# or
export OPENAI_API_KEY=your_key_here
```

`GraphRag/` 不需要預先建立任何 index:`nl_to_tio.py` 在執行期用 rdflib 直接讀 `TM Forum Intent Ontology/*.ttl`(`ontology_graph.py` + `subgraph_retriever.py`),以 typed traversal 取出子圖 context。無需 `graphrag index`。

KGE 線同樣只使用自己的 KGE artifacts(由 ontology TTL 訓練而來)。如果 ontology 有變更或 artifacts 不存在,再執行:

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/KGE/KGE-based-graphrag
python -m kge.train
```

### 0.2 KAG 線專屬準備(Docker stack + 獨立 venv + 灌料)

KAG 線需要 OpenSPG Docker 後端(`server / Neo4j / MySQL / MinIO`)+ 獨立 Python venv(避免跟主環境衝突)+ knext CLI + 預先灌料。完整步驟見 [`KAG/example_project/README.md`](KAG/example_project/README.md);摘要:

```bash
# (1) 啟 Docker stack
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/KAG
docker compose -f docker-compose-west.yml up -d

# (2) 啟 KAG venv(KAG package 已 editable install 進去)
source .venv/bin/activate
set -a && source /Users/grantyeh/Grant/Project/CHT/.env && set +a

# (3) 渲染 kag_config.yaml(.env 中的 key/model 帶入 Jinja2 template)
cd example_project
./render_config.sh

# (4) 註冊專案 + 推 schema + 灌料
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
knext schema commit
python builder/indexer.py        # 灌 16 個 SKILL.md → ~8500 個 Neo4j node(~6 min / ~$5)
```

> ⚠️ **patch 提醒**:KAG 0.8.0 對 OpenAI 官方 API 有 2 個必須的 source patch(`chat_template_kwargs` 與 `max_completion_tokens`),已套用於 `KAG/openspg-kag/`(被 .gitignore 排除)。Re-clone KAG 後須重新 apply,詳見 [`KAG/PATCHES.md`](KAG/PATCHES.md)。

## 1. 生成 TIO Turtle

### 一鍵生成四條線

從根目錄執行:

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python run_all_experiments.py
```

這會依序執行:

- `LLM-only/nl_to_tio.py`
- `GraphRag/nl_to_tio.py`
- `KGE/KGE-based-graphrag/nl_to_tio.py`
- `KAG/nl_to_tio.py`(需先完成 §0.2 KAG 灌料準備)

注意:`run_all_experiments.py` 預設不只生成,也會接著做評分與比較。

### 單獨生成 LLM-only

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/LLM-only
python nl_to_tio.py
```

輸出:

```text
tio_outputs/llm_only/*.ttl
```

### 單獨生成 GraphRag

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/GraphRag
python nl_to_tio.py
```

輸出:

```text
tio_outputs/graphrag/*.ttl
```

### 單獨生成 KGE

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/KGE/KGE-based-graphrag
python nl_to_tio.py
```

輸出:

```text
tio_outputs/kge/*.ttl
```

### 單獨生成 KAG

需先完成 §0.2 的 docker stack + venv + 灌料準備。`KAG/.venv` 不同於主環境,要用它自己的 Python:

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/KAG
source .venv/bin/activate
set -a && source /Users/grantyeh/Grant/Project/CHT/.env && set +a
python nl_to_tio.py                 # 全 20 題
# 或:
python nl_to_tio.py --case TC001 --verbose   # 試水單題
python nl_to_tio.py --limit 3 --verbose      # 跑前 3 題
```

輸出:

```text
tio_outputs/kag/*.ttl
```

> 每題 ~30-60 秒(retrieve 5-way ~20s + planner LLM + generator LLM + 我們的 Turtle LLM)。全 20 題約 10-15 分鐘 / ~$2 USD。

## 2. 評分 TIO Turtle

評分器是根目錄的 `evaluate_ttl.py`。它固定讀取：

- 測資：`test_cases_20.json`
- 生成結果：`tio_outputs/<experiment>/*.ttl`
- 評分輸出：`phase1/phase1_<experiment>.json`

### 一鍵重算四條線評分

如果 Turtle 已經生成好,只想重算評分與比較:

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python run_all_experiments.py --eval-only
```

### 單獨評分

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python evaluate_ttl.py llm_only       # 只評 LLM-only
python evaluate_ttl.py graphrag       # 只評 GraphRag
python evaluate_ttl.py kge            # 只評 KGE
python evaluate_ttl.py kag            # 只評 KAG
python evaluate_ttl.py                # 不帶參數 = 一次評四條線
```

評分檔固定寫到:

```text
phase1/phase1_llm_only.json
phase1/phase1_graphrag.json
phase1/phase1_kge.json
phase1/phase1_kag.json
```

## 3. 比較四條線

比較器是根目錄的 `compare_reports.py`。它會一次讀取四份 `phase1_*.json` 評分報告,輸出四方平均分數、parse 成功率、覆蓋率與逐題差異。

### 一鍵產生全部比較

如果四份評分檔都存在:

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python run_all_experiments.py --eval-only
```

這會產生:

```text
phase1/compare_four_way.txt
```

### 手動比較四條線

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python compare_reports.py
```

## 最常用指令

完整跑一次 phase-1,也就是「生成 -> 評分 -> 比較」:

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python run_all_experiments.py
```

只重算「評分 -> 比較」,不重新呼叫 LLM / GraphRAG / KAG:

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python run_all_experiments.py --eval-only
```

關掉 few-shot 做 ablation:

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python run_all_experiments.py --no-few-shot
```

## 注意事項

- `run_all_experiments.py` 會覆寫固定檔名的 `phase1/phase1_*.json` 與 `phase1/compare_four_way.txt`,不是歷史紀錄系統。
- `evaluate_ttl.py` 評的是 TIO Turtle 格式與 expected element 覆蓋率,不等於完整網路語意正確率。
- 如果模型輸出 Markdown code fence,evaluator 會嘗試剝掉再 parse,但理想輸出仍應該是 pure TIO Turtle。
- **KAG 線跟其他三條 venv 隔離**:KAG 用 `KAG/.venv/` 獨立環境(避免 openspg-kag 50+ deps 跟主環境衝突),`run_all_experiments.py` 跑 KAG 那段時要確保 PATH 上有 `KAG/.venv/bin/python`(或讓主 venv 已 import 過 `kag` package)。試水可以用 `python -c "import kag"` 確認。
