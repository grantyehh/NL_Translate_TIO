# TIO_Experiment — AGENTS.md

> 本檔給 Codex(以及未來接手的合作者)做為本目錄的操作守則。

## 1. 誰在用這個 repo

**使用者:睿丞**,CHT 意圖驅動網路專案三人組之一。

**負責範疇**:NL → TIO Turtle 的方法研究與品質提升。唯一交付是高品質的 TIO Turtle 輸出。下游 TMF chain / 設備層 / 驗證 / 部署都是他人責任。

**團隊與相關 repo**(`/Users/grantyeh/Grant/Project/CHT/` 底下):
- `TIO_Experiment/`(本 repo,睿丞主) — NL→TIO Turtle 多方法對比實驗
- `tio-agent-orchestrator/`(翊婕 / 睿丞曾共同碰過) — TIO Turtle→TMF chain→netconfig 的 agentic orchestrator
- `intent-vpn-lab/`(彥廷主) — 真實 GNS3 MPLS L3VPN 基礎設施 + NETCONF/Ansible/驗證/監控

## 2. 這個 repo 在做什麼

比較**四條** NL → TIO Turtle 生成 pipeline,用相同評分器評估品質。所有四條共用同一個 LLM 模型(目前為 `gpt-5.4`),以維持比較條件公平。

| 方法 | 目錄 | 核心思路 |
|---|---|---|
| LLM-only | `LLM-only/` | 純 LLM + few-shot,做 baseline |
| GraphRAG | `GraphRag/` | **ontology-aware domain-graph RAG**:entry-point grounding(lexical-exact + vector)→ 只走有意義連接屬性的有界 traversal(排除 rdf:type/subClassOf/domain/range plumbing)→ role-scoped 封閉詞表 + 自含 `@prefix` context |
| KGE | `KGE/KGE-based-graphrag/` | **正統 KGE**:text-embedding dense grounding + TransE link-prediction 排序「真實 triple」(永不合成),共用 GraphRAG 輸出契約(`resource_index`/`graph_relations`/`context_builder`)。pipeline 在 `kge/`(`select.py` / `paths.py` / `retrieve.py` / `train.py`) |
| KAG | `KAG/` | OpenSPG/KAG kg-builder + 5-way solver retrieval(atomic_query / outline / summary / vector / table)+ LLM。後端是 Docker stack(server + Neo4j + MySQL + MinIO) |

此外:
- **`tio-agent/`**(獨立 PoC,**不在四條 pipeline 內**):Bun + TypeScript 寫的 OpenAI-compatible agent loop + MCP(fake EVSLA network + tio-validator)+ local skills,只處理 Enterprise VPN hub-and-spoke SLA。有自己的 [`tio-agent/AGENTS.md`](./tio-agent/README.md),不重複內容

**共用基礎設施**:`test_cases_20.json`(20 題測資)、`few_shot_samples.json`、`evsla_prompt.py`、`evaluate_ttl.py`、`compare_reports.py`、`docs/standard.md`、`TM Forum Intent Ontology/*.ttl`。

**評分器現況**:品質評分是 `semantic_eval.py`(11 維 graph-binding composite),不是早期的 ICM/ontology/node 指標。強配方(`test_cases_20`)四條已飽和到 composite ~1.0,無鑑別力;**目前的主戰場是 structure-only(`test_cases_40`,抽掉 EVSLA 詞彙、只靠 retrieval 供詞)**。

**目前結果**(structure-only,40 題,strict `semantic_eval`,gpt-5.4;**完整與最新數據以 `progress.md` 為準**):

```
Line                       | Composite | Tok/case
LLM-only strong(天花板)    |  0.9722   |  5,349
GraphRAG-structure         |  0.9827   |  2,722
KGE-structure(正統)       |  0.9831   |  2,637
LLM-only-structure(地板)   |  0.0000   |  1,432
```

- **兩條 retrieval 皆 ≈/超過天花板品質,token 只用約一半** — 四維度 grounding(tenant/time_window/measurement_method/topology)+ ontology-domain scorer 對齊後達成(progress.md Architecture 5)。
- 待辦:OpenAI 配額恢復後三條 structure-only 正式重跑,刷新乾淨的輸出與 token ledger。

## 3. 目錄與資料流

```
NL (test_cases_20.json)
  → <method>/nl_to_tio.py
  → tio_outputs/<llm_only|graphrag|kge|kag>/TC*.ttl
  → evaluate_ttl.py <method>
  → phase1/phase1_<method>.json
  → compare_reports.py
  → phase1/output_quality/compare_four_way.txt
```

固定輸出位置(不要寫到別處,評分器跟比較器是 hard-code 路徑):
- 生成:`tio_outputs/<experiment>/*.ttl`
- 評分:`phase1/phase1_<experiment>.json`
- 比較:`phase1/output_quality/compare_four_way.txt`

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
`evaluate_ttl.py` 評的是 **TIO Turtle 格式 + expected element 覆蓋率**,不等於完整網路語意正確率。Markdown code fence 會嘗試剝掉再 parse,但理想輸出應是 pure TIO Turtle。

### 4.6 `run_all_experiments.py` 會覆寫
預設覆寫固定檔名的 `phase1/phase1_*.json` 與 `phase1/output_quality/compare_four_way.txt`,**不是歷史紀錄系統** — 要保留歷史結果自己另存。

### 4.7 當前分支
- **`retrieval-four-dim-grounding`**(2026-06-16):四維度 grounding(ontology 內建 metric→method/window 慣例 + 共用 retrieval 層修 reachability)+ ontology-domain scorer 對齊。GraphRAG/KGE structure-only composite 拉到 0.98。
- 主線歷史:`main`(canonical KGE + GraphRAG domain-graph redesign)、舊 `new-methods`。

### 4.8 `progress.md` 是現況的權威紀錄
`progress.md` 是逐輪實驗結果的單一真實來源(Architecture 1→5),重跑後**手動更新**,沒有自動同步。文字比較報告在 `phase1/output_quality/compare_four_way.txt`(品質)與 `phase1/token_usage/compare_token_usage*.txt`(token);這些是 `run_all_experiments.py` / `compare_*` 覆寫式產生,不是歷史系統。

## 5. 常用指令

```bash
# 完整 Phase 1:生成 → 評分 → 比較
python run_all_experiments.py

# 只重算評分 + 比較(Turtle 已生成)
python run_all_experiments.py --eval-only

# 關閉 few-shot 做 ablation
python run_all_experiments.py --no-few-shot

# 單條方法
cd LLM-only && python nl_to_tio.py
cd GraphRag && python nl_to_tio.py
cd KGE/KGE-based-graphrag && python nl_to_tio.py
# KAG(獨立 venv + Docker stack):見 KAG/example_project/README.md

# 重訓 KGE artifacts(TTL 變更或 artifacts 不存在時)
cd KGE/KGE-based-graphrag && python -m kge.train

# 單條評分 / 比較
python evaluate_ttl.py graphrag    # 不帶參數 = 一次評四條
python compare_reports.py

# tio-agent(獨立 PoC)
cd tio-agent && bun install && OPENAI_API_KEY=sk-... bun run agent
```

## 6. 工作慣例

- **新方法 / 改 retrieval 策略前**:先看 `progress.md` 與 `phase1/output_quality/compare_four_way.txt` 看當前狀態
- **跨方法比較前**:確認四條線都是相同 model / few-shot 設定下產生,否則結論不可信
- **改 ontology(TTL)**:GraphRag 執行期直接讀 TTL,免重建;KGE artifacts 需 retrain(`python -m kge.train`)
- **重跑實驗後**:同步更新 `progress.md` 的結果表(`compare_four_way.txt` 不會自動 propagate 到文字報告)
- **commit message**:依現有 git log style,Conventional Commits 但不強制 scope

## 7. 跟其他 repo 的關係

- `tio-agent-orchestrator/tests/fixtures/tio_experiment/graphrag/` 是這邊 `tio_outputs/graphrag/` 的**舊快照**,只用來測 orchestrator。若兩邊不一致以本 repo 為準
- 翊婕的 orchestrator 會以本 repo 產出的 TIO Turtle 作為輸入。Turtle 品質直接影響下游 TMF chain 能否消費 — 但下游邏輯不是本 repo 範疇,**不要在這邊重新實作 TMF chain**

## 8. 不負責的事

- TMF chain(TMF921 / 638 / 657 / 653)— 翊婕
- 設備推送、NETCONF、GNS3 部署、三層驗證 engine、監控 — 彥廷
- 整條 pipeline 編排與多租戶 session 管理 — 翊婕

## 9. Roadmap / Open work

- [ ] **三條 structure-only 正式重跑**(待 OpenAI 配額恢復):驗證 few-shot/骨架的 expectation-placement 生成端效果,並刷新乾淨的輸出與 token ledger(現行 GraphRAG ledger 為 git 還原+合併)。
- [ ] **scorer 嚴格化(可選)**:重跑後可把 `semantic_eval` 從 expectation-first/target-fallback 收成 expectation-only,真正強制 ontology domain(現為寬鬆相容)。
- [ ] **`kag-logical-form-grounding`**(未來可能方向,不一定執行):把 logical form 接到 ontology grounding 的探索路線。尚未開分支
- [ ] 進入 Phase 2(若有規劃)
