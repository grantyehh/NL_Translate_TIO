# TIO_EVSLA_QA — KAG Example Project

KAG 線(NL → TIO JSON-LD)的最小可跑專案。對齊 `LLM-only/`、`GraphRag/`、`KGE/` 既有 pipeline 的輸出契約,但保留 KAG 原生的 builder + solver 結構。

## 為什麼這樣搭

走 KAG 預設文字 auto-extraction 路線(Approach A — 跟 `kag/examples/NetOperatorQA` 同款結構),原因:
- KAG schema-driven 路徑(Approach B/C)沒現成 example,改 builder 內部 API 風險高
- 我們手寫的 `TIO_Experiment/KAG/schema/TIO_EVSLA.schema` 是 Approach B/C 用的,**這個 example_project 暫時用不上**;若 A 跑出來不滿意,再切 B/C
- 完整討論見 [`../schema/README.md`](../schema/README.md)

查詢端改造後走 KAG 原生 solver:

```text
NL intent
  -> kag_static_pipeline planner
  -> kag_hybrid_retrieval_executor
  -> tio_turtle_generator
  -> TIO Turtle
```

`KAG/nl_to_tio.py` 不再把 retrieved chunks 拿出來交給外部 OpenAI call 生成 JSON-LD;final JSON-LD 由 KAG solver 的 generator 階段產生。

## 目錄結構

```
example_project/
├── kag_config.yaml          ← project / builder / solver 設定;LLM key 走 GRAPHRAG_API_KEY env
├── builder/
│   ├── data/                ← 16 份 corpus (從 tio-agent/skills/<name>/SKILL.md 複製)
│   │   ├── tio-enterprise-vpn-sla.md       ← EVSLA 領域詞彙
│   │   ├── tio-intent-common-model.md      ← ICM 基底
│   │   ├── tio-quantity.md                 ← Quantity ontology
│   │   ├── tio-metrics-observations.md     ← Metrics
│   │   ├── tio-logical-operators.md
│   │   ├── tio-set-operators.md
│   │   ├── tio-math-functions.md
│   │   ├── tio-function-ontology.md
│   │   ├── tio-intent-guarantee.md
│   │   ├── tio-intent-management.md
│   │   ├── tio-intent-probing.md
│   │   ├── tio-intent-specification.md
│   │   ├── tio-intent-validity.md
│   │   ├── tio-preference.md
│   │   ├── tio-proposal-best-intent.md
│   │   └── tio-utility.md
│   └── indexer.py           ← 跑 builder 把 data/ 灌成 KG
├── schema/
│   └── TIO_EVSLA_QA.schema  ← NetOperatorQA 通用 schema(Document/Chunk/Outline/Summary/Table/KnowledgeUnit/AtomicQuery)
├── solver/
│   └── tio_turtle_generator.py ← KAG generator + prompt,產生 final TIO Turtle
└── reasoner/                ← (KAG 預設目錄,暫空)
```

## 跑法

### 0. 先決條件

- Docker stack 已起(`../docker-compose-west.yml`)
- KAG package 已裝(`../.venv` 內)
- `GRAPHRAG_API_KEY` 已 export 到環境(對應 OpenAI / OpenAI-compat 端點)

### 1. 啟用 venv + 載 env

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/KAG
source .venv/bin/activate
source /Users/grantyeh/Grant/Project/CHT/.env   # 或手動 export GRAPHRAG_API_KEY
cd example_project
```

### 2. 註冊專案到 OpenSPG server

```bash
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .
```

### 3. 推 schema(把 `TIO_EVSLA_QA.schema` 注入 graph)

```bash
knext schema commit
```

### 4. 灌資料(讀 builder/data/*.md → chunk → extract → write to Neo4j)

```bash
cd builder
python indexer.py
```

預期成本:
- 16 個 md × 1000-char chunk(平均每檔 5-10 chunk)≈ 100-200 chunks
- 每 chunk 5 個 extractor(chunk / outline / summary / table / atomic_query)有 4 個會打 LLM
- LLM 呼叫量約 400-800 calls(視 chunk 數)
- 估 30-60 分鐘,預算 < $10 USD(gpt-5.4)

### 5. 驗證 graph 有資料

```bash
# Neo4j browser
open http://localhost:7474/
# 帳號:neo4j / neo4j@openspg
# Cypher 範例:
#   MATCH (n) RETURN labels(n), count(*)
#   MATCH (n:`TIO_EVSLA_QA.Chunk`) RETURN n LIMIT 10
```

## 跟其他兩條 pipeline 的對應

| Phase | LLM-only | GraphRag | KGE-hybrid | **KAG (this)** |
|---|---|---|---|---|
| Corpus | (none — only few-shot) | `graphrag_term_input/` 從 TTL 切 | 同 GraphRag + KGE triples | `builder/data/*.md` 從 SKILL.md |
| 知識存儲 | (LLM 內) | lancedb 向量索引 | + entity TransE embedding | Neo4j graph(chunks + outline/summary/atomic_query/table) |
| Retrieval | (無) | community summary + 向量 | 同 + KGE entity 相似 | 5-way ensemble(atomic_query / outline / summary / vector / table) |
| Generation | LLM + few-shot | LLM + context + few-shot | 同 | KAG solver generator + 5-way context + few-shot |

## 後續 task

- [x] task #10:讓 `KAG/nl_to_tio.py` 走 KAG solver generator 產生 JSON-LD
- [ ] task #11:跑全量 KAG 輸出並重新做 4-way 比較
