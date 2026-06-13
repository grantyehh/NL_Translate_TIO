# TIO_Experiment — AGENTS.md

> 本檔給 Codex(以及未來接手的合作者)做為本目錄的操作守則。

## 1. 誰在用這個 repo

**使用者:睿丞**,CHT 意圖驅動網路專案三人組之一。

**負責範疇**:NL → TIO JSON-LD 的方法研究與品質提升。唯一交付是高品質的 TIO JSON-LD 輸出。下游 TMF chain / 設備層 / 驗證 / 部署都是他人責任。

**團隊與相關 repo**(`/Users/grantyeh/Grant/Project/CHT/` 底下):
- `TIO_Experiment/`(本 repo,睿丞主) — NL→JSON-LD 多方法對比實驗
- `tio-agent-orchestrator/`(翊婕 / 睿丞曾共同碰過) — JSON-LD→TMF chain→netconfig 的 agentic orchestrator
- `intent-vpn-lab/`(彥廷主) — 真實 GNS3 MPLS L3VPN 基礎設施 + NETCONF/Ansible/驗證/監控

## 2. 這個 repo 在做什麼

比較**四條** NL → TIO JSON-LD 生成 pipeline,用相同評分器評估品質。所有四條共用同一個 LLM 模型(目前為 `gpt-5.4`),以維持比較條件公平。

| 方法 | 目錄 | 核心思路 |
|---|---|---|
| LLM-only | `LLM-only/` | 純 LLM + few-shot,做 baseline |
| GraphRAG | `GraphRag/` | **typed RDF traversal**(不是 Microsoft GraphRAG CLI),從 TM Forum Intent Ontology TTL 抓 query-specific subgraph |
| KGE | `KGE/KGE-based-graphrag/` | text grounding + TransE neighborhood expansion + **link prediction** + LLM。pipeline 在 `kge/`(`paths.py` / `retrieve.py` / `tio_triples.py` / `train.py`);`tio_to_text.py` 把 triple 轉成 text 供 prompt |
| KAG | `KAG/` | OpenSPG/KAG kg-builder + 5-way solver retrieval(atomic_query / outline / summary / vector / table)+ LLM。後端是 Docker stack(server + Neo4j + MySQL + MinIO) |

此外:
- **`tio-agent/`**(獨立 PoC,**不在四條 pipeline 內**):Bun + TypeScript 寫的 OpenAI-compatible agent loop + MCP(fake EVSLA network + tio-validator)+ local skills,只處理 Enterprise VPN hub-and-spoke SLA。有自己的 [`tio-agent/AGENTS.md`](./tio-agent/README.md),不重複內容

**共用基礎設施**:`test_cases_20.json`(20 題測資)、`few_shot_samples.json`、`evsla_prompt.py`、`evaluate_jsonld.py`、`compare_reports.py`、`docs/standard.md`、`TM Forum Intent Ontology/*.ttl`。

**Phase 1 目前結果**(`new-methods` 分支,讀自 `phase1/compare_four_way.txt`):

```
Experiment | Parse OK | Avg ICM | Avg ontology | Avg metric | Avg nodes | Verbosity OK | Node ratio
LLM-only   |  95.00%  | 0.8975  |   0.0000     |   0.0000   |   39.50   |    25.00%    | 0.6436
GraphRag   | 100.00%  | 1.0000  |   0.9889     |   1.0000   |   62.65   |   100.00%    | 1.0186
KGE        |  95.00%  | 1.0000  |   0.9972     |   1.0000   |   63.40   |     0.00%    | 0.0000
KAG        | 100.00%  | 0.9900  |   0.9314     |   1.0000   |   61.80   |   100.00%    | 1.0031
```

- **Ontology coverage 最佳:KGE(0.9972)** — link prediction 版本領先
- **ICM / metric coverage 最佳:GraphRag(1.0000),KGE 並列**
- **Verbosity:KGE 0%** — node 數超出 budget,是改進方向
- 舊版 `KGE-hybrid` 結果留在 `phase1_kge_hybrid.json` / `compare_three_way.txt` 作對照,不再參與 four-way

## 3. 目錄與資料流

```
NL (test_cases_20.json)
  → <method>/nl_to_tio.py
  → jsonld_outputs/<llm_only|graphrag|kge|kag>/TC*.jsonld
  → evaluate_jsonld.py <method>
  → phase1/phase1_<method>.json
  → compare_reports.py
  → phase1/compare_four_way.txt
```

固定輸出位置(不要寫到別處,評分器跟比較器是 hard-code 路徑):
- 生成:`jsonld_outputs/<experiment>/*.jsonld`
- 評分:`phase1/phase1_<experiment>.json`
- 比較:`phase1/compare_four_way.txt`

## 4. 關鍵運作規則

### 4.1 venv 隔離
- **主 venv**(`.venv/`):LLM-only / GraphRAG / KGE 共用
- **KAG venv**(`KAG/.venv/`):獨立,因為 openspg-kag 50+ 依賴會跟主環境衝突。`run_all_experiments.py` 跑 KAG 段時要確保 PATH 上是 `KAG/.venv/bin/python`
- **`tio-agent/`**:Bun runtime,跟以上完全分開

### 4.2 API key 來源
- 主環境:`GRAPHRAG_API_KEY` 或 `OPENAI_API_KEY`(env var)
- KAG:`/Users/grantyeh/Grant/Project/CHT/.env`(set -a 載入後再跑)
- tio-agent:`OPENAI_API_KEY` 直接 inline 或 .env

### 4.3 KAG 0.8.0 patch
KAG 0.8.0 對 OpenAI 官方 API 有 2 個必須的 source patch(`chat_template_kwargs` 與 `max_completion_tokens`),套用在 `KAG/openspg-kag/`(被 `.gitignore` 排除)。Re-clone KAG 後須重新 apply,詳見 `KAG/PATCHES.md`。

### 4.4 模型一致性
四條 pipeline 共用同一 LLM(目前 `gpt-5.4`),變更時要四條同步更新,否則跨方法比較不可信。

### 4.5 評分器涵義
`evaluate_jsonld.py` 評的是 **JSON-LD 格式 + expected element 覆蓋率**,不等於完整網路語意正確率。Markdown code fence 會嘗試剝掉再 parse,但理想輸出應是 pure JSON-LD。

### 4.6 `run_all_experiments.py` 會覆寫
預設覆寫固定檔名的 `phase1/phase1_*.json` 與 `phase1/compare_four_way.txt`,**不是歷史紀錄系統** — 要保留歷史結果自己另存。

### 4.7 當前分支
- **`new-methods`**(2026-05-24):GraphRAG typed traversal + KGE link prediction(後者由 `kge-link-prediction` merge 進來)
- 其他存活分支:`main`(舊版)、`kge-link-prediction`(已 merge)、`new-CHT`
- Remote `graphrag-typed-traversal` 是 GraphRAG 改寫的歷史分支,內容已在 `new-methods` 裡

### 4.8 `progress.md` 與實際結果可能不同步
`progress.md` 的 Phase 1 結果表是 2026-05-19 GraphRAG typed traversal 完成時的快照,**KGE 還是 hybrid 舊版**。現況數據以 `phase1/compare_four_way.txt`(及對應的 `phase1_*.json`)為準。重跑後要手動更新 `progress.md`,沒有自動同步。

## 5. 常用指令

```bash
# 完整 Phase 1:生成 → 評分 → 比較
python run_all_experiments.py

# 只重算評分 + 比較(JSON-LD 已生成)
python run_all_experiments.py --eval-only

# 關閉 few-shot 做 ablation
python run_all_experiments.py --no-few-shot

# 單條方法
cd LLM-only && python nl_to_tio.py
cd GraphRag && python nl_to_tio.py
cd KGE/KGE-based-graphrag && python nl_to_tio.py
# KAG(獨立 venv + Docker stack):見 KAG/example_project/README.md

# 重建 GraphRAG ontology input(TTL 變更時)
python GraphRag/build_graphrag_input.py

# 重訓 KGE artifacts(TTL 變更或 artifacts 不存在時)
cd KGE/KGE-based-graphrag && python -m kge.train

# 單條評分 / 比較
python evaluate_jsonld.py graphrag    # 不帶參數 = 一次評四條
python compare_reports.py

# tio-agent(獨立 PoC)
cd tio-agent && bun install && OPENAI_API_KEY=sk-... bun run agent
```

## 6. 工作慣例

- **新方法 / 改 retrieval 策略前**:先看 `progress.md` 與 `phase1/compare_four_way.txt` 看當前狀態
- **跨方法比較前**:確認四條線都是相同 model / few-shot 設定下產生,否則結論不可信
- **改 ontology(TTL)**:要先重建 `graphrag_term_input/`,GraphRAG index 也要重建一次;KGE artifacts 要 retrain
- **重跑實驗後**:同步更新 `progress.md` 的結果表(`compare_four_way.txt` 不會自動 propagate 到文字報告)
- **commit message**:依現有 git log style,Conventional Commits 但不強制 scope

## 7. 跟其他 repo 的關係

- `tio-agent-orchestrator/tests/fixtures/tio_experiment/graphrag/TC*.jsonld` 是這邊 `jsonld_outputs/graphrag/` 的**舊快照**,只用來測 orchestrator。若兩邊不一致以本 repo 為準
- 翊婕的 orchestrator 會以本 repo 產出的 JSON-LD 作為輸入。JSON-LD 品質直接影響下游 TMF chain 能否消費 — 但下游邏輯不是本 repo 範疇,**不要在這邊重新實作 TMF chain**

## 8. 不負責的事

- TMF chain(TMF921 / 638 / 657 / 653)— 翊婕
- 設備推送、NETCONF、GNS3 部署、三層驗證 engine、監控 — 彥廷
- 整條 pipeline 編排與多租戶 session 管理 — 翊婕

## 9. Roadmap / Open work

- [ ] **`kag-logical-form-grounding`**(未來可能方向,不一定執行):把 logical form 接到 ontology grounding 的探索路線。尚未開分支
- [ ] **KGE verbosity 修正**:目前 Avg node 63.40 超出 budget(Verbosity OK 0%),要研究壓縮策略
- [ ] **四條同條件正式重跑**:`progress.md` 提醒過,目前 KGE 是 link-prediction 新版但其他三條的最終比較需確認都是同一輪
- [ ] 進入 Phase 2(若有規劃)
