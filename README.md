# CHT TIO Turtle Experiments

這個專案比較**四條** NL -> TIO Turtle 生成流程：

- `LLM-only/`: 只用 LLM + few-shot。
- `GraphRag/`: **ontology-aware domain-graph RAG**(entry-point grounding〔lexical-exact + vector〕→ 只走有意義連接屬性的有界 traversal〔排除 rdf:type/subClassOf/domain/range plumbing〕→ role-scoped 封閉詞表 → 自含 `@prefix` context)+ LLM + few-shot。
- `KGE/KGE-based-graphrag/`: **正統 KGE**(text-embedding dense grounding + TransE link-prediction 排序「真實 triple」〔永不合成〕,共用 GraphRAG 輸出契約)+ LLM + few-shot。
- `KAG/`: OpenSPG/KAG kg-builder + 5-way solver retrieval(atomic_query / outline / summary / vector / table)+ LLM + few-shot。後端走 Docker stack(server + Neo4j + MySQL + MinIO)。詳見 [`KAG/example_project/README.md`](KAG/example_project/README.md)。

> GraphRag 與 KGE 的 retrieval 架構詳解見 [`retrieval_arch.md`](retrieval_arch.md);structure-only 替代性實驗的操作見 §4,逐輪結果見 `progress.md`(Experiment Architecture 3→6)。

四條線共用：

- `test_cases_20.json`: 原 20 題測資。`test_cases_40.json`: 20 題 + 20 題新增 hub-and-spoke 案(TC021–040,structure-only 實驗用)。
- `few_shot_samples.json`: 強配方 few-shot(含 EVSLA 詞彙)。`few_shot_structure_only.json`: structure-only 用的 sanitized skeleton few-shot(佔位符、無 EVSLA 詞彙)。
- `evsla_prompt.py`: 共用 EVSLA system prompt 組裝(profile: `strong` / `weak` / `structure_only`)。
- `evaluate_ttl.py`: TIO Turtle 評分器(含 `semantic_eval` 語意評分;支援 `--test-cases`)。
- `compare_reports.py`: 評分報告比較器。
- `docs/standard.md`: TIO 轉譯標準草案。

固定輸出位置:

- 生成結果:根目錄 `tio_outputs/<experiment>/*.ttl`。`<experiment>` ∈ 強配方 `llm_only / graphrag / kge / kag`、weak 配方 `*_weak`、structure-only 配方 `graphrag_structure / kge_structure / llm_only_structure`。
- 評分結果:`phase1/phase1_<experiment>.json`
- 比較結果:`phase1/output_quality/compare_four_way.txt`(品質)、`phase1/token_usage/compare_token_usage.txt`(token)

## 0. 前置準備

### 0.1 LLM-only / GraphRag / KGE 共用環境

在專案根目錄啟用環境並安裝依賴:

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
source .venv/bin/activate
python -m pip install -r requirements.txt
```

預設使用 OpenAI API,需要設定其中一個 API key:

```bash
export GRAPHRAG_API_KEY=your_key_here
# or
export OPENAI_API_KEY=your_key_here
```

若要改用 Azure AI Foundry / Azure OpenAI v1 endpoint:

```bash
export OPENAI_PROVIDER=azure
export AZURE_OPENAI_ENDPOINT=https://cht-tio.services.ai.azure.com/openai/v1
export AZURE_OPENAI_DEPLOYMENT=gpt-5.4
export AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
az login
```

也可改用 Azure API key:

```bash
export AZURE_OPENAI_API_KEY=your_azure_key_here
```

若 embedding 使用另一組 Azure key 或 endpoint:

```bash
export AZURE_OPENAI_EMBEDDING_API_KEY=your_embedding_key_here
export AZURE_OPENAI_EMBEDDING_ENDPOINT=https://your-embedding-resource.openai.azure.com/openai/v1
```

`GraphRag/` 的重設計版會用一個 **offline resource index**(完整 IRI + role 分類 + 文字 embedding)做向量 grounding。執行 structure-only 線或要向量 grounding 前,先建一次(會呼叫 embedding API):

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
python GraphRag/build_index.py --output-dir GraphRag/index   # 寫到 GraphRag/index/(已 gitignore)
python GraphRag/build_index.py --check                       # 只報狀態、不呼叫 API
```

> rdflib 讀 `TM Forum Intent Ontology/*.ttl` 與 connective traversal 仍是執行期完成;只有「向量 grounding 的 resource embedding」需要這個 index。沒有 index 時 grounding 退化為 lexical-only。

KGE 線使用自己的 KGE artifacts(由 ontology TTL 訓練:TransE entity/relation embedding + entity text embedding)。如果 ontology 有變更或 artifacts 不存在,再執行(需 API key,會寫到 `KGE/KGE-based-graphrag/kge_data/`,已 gitignore):

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/KGE/KGE-based-graphrag
python -m kge.train --embedding-model text-embedding-3-small
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

評分器是根目錄的 `evaluate_ttl.py`(格式檢查 + `semantic_eval` 11 維 graph-binding 語意評分)。它讀取：

- 測資：預設 `test_cases_20.json`,可用 `--test-cases test_cases_40.json` 改用 40 題 gold(structure-only 實驗用)
- 生成結果：`tio_outputs/<experiment>/*.ttl`
- 評分輸出：`phase1/phase1_<experiment>.json`

`<experiment>` 可為強配方 `llm_only / graphrag / kge / kag`、`*_weak`、或 structure-only `graphrag_structure / kge_structure / llm_only_structure`。

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
phase1/output_quality/compare_four_way.txt
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

## 4. Structure-only 替代性實驗(retrieval vs prompt-engineering)

研究問題:**system prompt 給「組裝骨架」、抽掉全部 EVSLA 詞彙時,retrieval 能否獨力把詞彙補回來?** 三條 structure-only 線共用 byte-identical 的 `structure_only` system prompt + 同一份 `few_shot_structure_only.json`(skeleton);唯一差別是 user message 裡有沒有 retrieval context:

- `graphrag_structure` = structure prompt + GraphRAG(domain-graph)retrieval
- `kge_structure` = structure prompt + KGE retrieval
- `llm_only_structure` = structure prompt + **無** retrieval(對照地板)
- 上界參考:`llm_only` 強配方(full prompt + 含詞彙 few-shot)

跑法(需 API key;先完成 §0.1 的 `build_index` 與 `kge.train`):

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment
cd GraphRag             && python nl_to_tio.py --prompt-profile structure_only --test-cases ../test_cases_40.json    && cd ..
cd LLM-only             && python nl_to_tio.py --prompt-profile structure_only --test-cases ../test_cases_40.json    && cd ..
cd KGE/KGE-based-graphrag && python nl_to_tio.py --prompt-profile structure_only --test-cases ../../test_cases_40.json && cd ../..

python evaluate_ttl.py graphrag_structure  --test-cases test_cases_40.json
python evaluate_ttl.py kge_structure       --test-cases test_cases_40.json
python evaluate_ttl.py llm_only_structure  --test-cases test_cases_40.json
```

最新結果(Architecture 6,2026-06-17 正式重跑;40 題,Azure `gpt-5.4`,strict `semantic_eval`;完整見 `progress.md`、架構詳解見 [`retrieval_arch.md`](retrieval_arch.md)):

```text
Line                       | Parse | Composite | Avg online tok | Prep tok
LLM-only strong(天花板)    | 100%  |  0.9738   |     5,354      |      0
GraphRAG-structure         | 100%  |  0.9746   |     2,718      | 14,365
KGE-structure(正統)       | 100%  |  0.9778   |     2,722      | 15,555
LLM-only-structure(地板)   |  95%  |  0.0000   |     1,532      |      0
```

- **兩條 retrieval 皆達到/略超天花板品質(KGE 0.9778 ≳ GraphRAG 0.9746 ≳ ceiling 0.9738),online token 只用約天花板的 51%**。token 要跟天花板 5,354 比,不是地板 1,532(地板是無 retrieval 對照,品質 0)。
- 達成靠四維度 grounding(tenant / time_window / measurement_method / topology):慣例編進 EVSLA TTL(metric→method、預設 window + 中文 NL 觸發 label),共用 retrieval 層保證四角色 reachability,structure-only 骨架要求 tenant 綁定 + 有型別 hub/spoke。
- scorer 對齊 ontology domain(SLA 綁定 predicate 的 `rdfs:domain` 是 `evsla:SlaExpectation`):evaluator 改成從 expectation 讀、target 作 fallback,修掉 TC025 的契約鏈誤判。
- prep token 攤到 @100 後 GraphRAG/KGE 仍約 2.86k/2.88k per case,明顯低於 ceiling。KGE 初跑 TC021/TC029 因局部 Turtle syntax parse fail,單題重跑修復後合併 ledger;後續可加 Turtle parse-retry/repair guard。

## 注意事項

- `run_all_experiments.py` 會覆寫固定檔名的 `phase1/phase1_*.json` 與 `phase1/output_quality/compare_four_way.txt`,不是歷史紀錄系統。
- `evaluate_ttl.py` 評的是 TIO Turtle 格式與 expected element 覆蓋率,不等於完整網路語意正確率。
- 如果模型輸出 Markdown code fence,evaluator 會嘗試剝掉再 parse,但理想輸出仍應該是 pure TIO Turtle。
- **KAG 線跟其他三條 venv 隔離**:KAG 用 `KAG/.venv/` 獨立環境(避免 openspg-kag 50+ deps 跟主環境衝突),`run_all_experiments.py` 跑 KAG 那段時要確保 PATH 上有 `KAG/.venv/bin/python`(或讓主 venv 已 import 過 `kag` package)。試水可以用 `python -c "import kag"` 確認。
