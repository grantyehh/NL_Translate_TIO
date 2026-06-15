# Progress Report: New Methods Branch

Conclusion recorded at: 2026-05-24 CST

## Current Status

目前 `new-methods` 分支已整合三條新版知識增強 pipeline 的 phase1 結果：

- GraphRAG typed RDF traversal
- KGE link-prediction hybrid
- KAG native builder + solver/generator

四條 pipeline 已完成同一組 `test_cases_20.json` 的 TIO Turtle 產出與 comparison report：

- `tio_outputs/graphrag/TC001.ttl` 到 `TC020.ttl`
- `tio_outputs/kge/TC001.ttl` 到 `TC020.ttl`
- `tio_outputs/kag/TC001.ttl` 到 `TC020.ttl`
- `phase1/phase1_graphrag.json`
- `phase1/phase1_kge.json`
- `phase1/phase1_kag.json`
- `phase1/compare_four_way.txt`

## GraphRAG

GraphRAG 已完成從原本 document-centric retrieval 改成 ontology-native typed traversal。

新版流程：

```text
user query
-> extract seed terms
-> ground seed terms to ontology URIs
-> typed BFS over RDF graph
-> serialize triples + comments
-> LLM generates TIO Turtle
```

已完成內容：

- `GraphRag/ontology_graph.py`: 載入 TTL、建立 label/comment/type index、執行 typed BFS。
- `GraphRag/subgraph_retriever.py`: seed extraction、seed-to-URI grounding、subgraph serialization。
- `GraphRag/nl_to_tio.py`: 改用 typed RDF traversal context 取代 Microsoft GraphRAG CLI context。
- 20 題 GraphRAG TIO Turtle 已重新產生並評估。

## KGE

KGE 已完成新版 KGE-hybrid 流程，將 ontology triples 轉成 graph embedding 訊號，再搭配 link prediction 補出可能需要的 triples。

新版目標：

```text
TTL triples
-> entity/relation embedding
-> NL mention grounding
-> link prediction
-> grounded URIs + predicted triples
-> LLM generates TIO Turtle
```

目前 KGE phase1 已重新產生 20 題輸出並納入四方比較。

## KAG

KAG 目前完成的是 **native KAG builder + solver/generator 版**，不是 `kag-logical-form-grounding` 改良版。

目前實際流程：

```text
builder/data/*.md
-> KAG builder builds KG into OpenSPG / Neo4j
-> KAG solver planning
-> KAG retrieval / reasoning
-> KAG generator emits TIO Turtle
-> evaluate_ttl.py
```

已完成內容：

- `KAG/docker-compose-west.yml` stack 已用於 OpenSPG / Neo4j / MySQL / MinIO。
- `KAG/example_project/builder/indexer.py` 已跑完 16 個 markdown corpus，0 failures。
- KAG solver 已完成 `TC001` 到 `TC020`。
- `KAG/nl_to_tio.py` 已支援 resume：
  - `--resume`: 跳過已存在且非空的輸出。
  - `--from-case TC014`: 從指定 case 往後跑。
- `KAG/example_project/solver/tio_turtle_generator.py` 已接到 KAG solver generator 階段，使用 KAG context 產生 TIO Turtle。
- KAG generator 直接吐 pure TIO Turtle，由 evaluator 解析。
- `KAG/test_nl_to_tio.py` 已加入 Turtle 產出測試。

注意：

- KAG builder 的 KG 實際寫入 Docker volume 內的 OpenSPG / Neo4j。
- `KAG/example_project/builder/ckpt/` 是本機 checkpoint/cache，可用於 builder resume，但不是 KG 本體。
- 目前 compose 使用 anonymous Docker volumes；若執行 `docker compose down -v`，KAG KG data 會被刪除。建議後續改成 named volumes。

## KAG Logical Form Grounding

`docs/comparison_plan.md` 中提到的 `kag-logical-form-grounding` 尚未實作。

該 variant 原本設計為：

```text
NL
-> logical form / slot frame
-> deterministic ontology grounding
-> schema validation
-> template render
-> TIO Turtle
```

尚未完成項目：

- logical form schema / slot frame parser
- NL -> logical form prompt
- slot value -> TTL URI deterministic mapping table
- SHACL 或 TTL domain/range schema validation
- grounded slots -> Turtle template render
- 獨立輸出目錄，例如 `tio_outputs/kag_logical_form/`
- evaluator / compare report 第五欄

因此目前比較中的 `KAG` 指的是 native KAG，而不是 logical-form-first KAG。

## Current Four-Way Evaluation

最新一輪：**2026-06-13 全四條重新生成**(strong prompt、gpt-5.4、text-embedding-3-small、few-shot 4)。

> ⚠️ 評分器/比較器已從 JSON-LD 時代轉成 Turtle 版。`evaluate_ttl.py` 產出簡化 schema
> (parse_ok / expected_coverage_ratio / triple_count / unknown_predicates·types /
> intent_uri / markdown_fence);`compare_reports.py` 已於本輪對齊(commit `920c6cc`),
> 讀 `phase1/phase1_<line>.json` 並輸出下列欄位。舊的 ICM/ontology/metric/node-ratio
> 欄位是 JSON-LD evaluator 的指標,現行 Turtle evaluator **不再產出**。

目前 `phase1/output_quality/compare_four_way.txt` 結果：

```text
Experiment     | Cases | Parse OK   | Avg coverage | Cov=100%   | Avg triples  | Pure TTL   | Unk pred  | Unk type  | Intent ID OK
LLM-only       |    20 |    100.00% |       1.0000 |    100.00% |        36.70 |    100.00% |         0 |         0 |       100.00%
GraphRag       |    20 |    100.00% |       1.0000 |    100.00% |        36.40 |    100.00% |         0 |         0 |       100.00%
KGE            |    20 |    100.00% |       1.0000 |    100.00% |        35.80 |    100.00% |         0 |         0 |       100.00%
KAG            |    20 |    100.00% |       1.0000 |    100.00% |        35.95 |    100.00% |         0 |         0 |       100.00%
```

目前觀察：

- **品質四方並列、全部頂格**:四條都 100% parse、expected coverage 1.0000、零非 TIO 詞彙
  (unknown predicate/type 皆 0)、輸出皆 pure Turtle(無 markdown fence)、intent URI 全帶對 case id。
- 在**強 prompt** 下,現行 evaluator **無法區分四條品質** —— 強 prompt 已把 schema/metric mappings
  手寫進去,retrieval 的語意貢獻被天花板遮蔽。這是啟動 weak-prompt 替代性實驗的直接動機
  (spec: `docs/superpowers/specs/2026-06-13-weak-prompt-retrieval-substitution-design.md`)。
- 唯一能分出高下的是**成本**(見下節 token):本輪三條品質相同,但 GraphRag 用了約 5.7× token。
- LLM-only 仍為主要 baseline(無 ontology retrieval / graph reasoning / grounding)。

## Semantic Evaluator (stricter, 2026-06-14)

為了打破上面「四方品質全 100% 平手」的天花板,新增 graph-binding 語意評分器
(`semantic_eval.py`,擴充進 `evaluate_ttl.py`,結果見 `compare_four_way.txt` 的
Semantic Summary)。它沿 intent 契約路徑綁定每個 gold metric 到輸出子圖,逐維度比對
**正確性**(非僅存在性):metric / threshold值+單位 / statistic / scope / method /
time_window / operator / tenant / topology / contract / precision,加權成 composite。
設計與計畫:`docs/superpowers/specs/2026-06-14-stricter-semantic-evaluator-design.md`、
`docs/superpowers/plans/2026-06-14-stricter-semantic-evaluator.md`。

本輪(strong prompt)結果:

```text
Experiment | Composite | (除下列外各維度皆 1.00)
LLM-only   |  0.9355   | operator 0.00
GraphRag   |  0.9355   | operator 0.00
KAG        |  0.9323   | operator 0.00 ; topology 0.95 (TC010)
KGE        |  0.9226   | operator 0.00 ; topology 0.80 (TC001/002/017/019)
```

關鍵發現(舊評分器全看不到):

- **嚴格評分器打破了 100% 平手**:KGE 排最後、KAG 次低。
- **topology 拉開差距**:**KGE 4 題產出殘缺拓樸**(`evsla:HubAndSpokeTopology` 有 hub、
  但缺 `evsla:hasSpoke`/SpokeSite),KAG 1 題(TC010);LLM-only / GraphRag 完整。
- **operator 整排 0/20**:無任何方法用 `quan:smaller/atLeast` 顯式建模比較方向(全靠
  metric 隱含)。是 weak-prompt + retrieval 的潛在分水嶺。
- 核心語意(metric/threshold/statistic/scope/method/time_window/tenant/contract/
  precision)四條都滿分 —— strong prompt 已手寫保證,差異只在 prompt 未管的 topology
  完整性與 operator。

> 上表是 **operator 尚未進 gold(commit `2e20eb8`)** 的基線:operator 全 0、composite ~0.92–0.94。

## Experiment Architecture 1 — strong prompt + operator-in-gold (2026-06-15)

把**顯式比較方向(operator)**寫進 gold few-shot + 兩個生成 prompt(TIO-忠實 pattern:
`log:Condition` 以 `quan:smaller`/`quan:atLeast` 當謂詞,套用到 `met:observedValue` 取出的
觀測量與共用 threshold 節點;spec `2026-06-15-operator-pattern-design.md`)。四條全用
strong prompt + operator-enriched few-shot 重生成,嚴格語意評分器(11 維度)結果:

```text
Line     | Parse | Composite | operator | topology | (其餘 9 維度)
LLM-only |  100% |  1.0000   |   1.00   |   1.00   | 全 1.00
GraphRag |  100% |  1.0000   |   1.00   |   1.00   | 全 1.00
KGE      |  100% |  1.0000   |   1.00   |   1.00   | 全 1.00
KAG      |  100% |  0.9968   |   1.00   |   0.95   | 全 1.00  (TC010 拓樸缺 spoke)

tokens   | total     | per_case
LLM-only |  104,438  |  5,221
GraphRag |  509,809  | 25,490   (~4.9× LLM-only;retrieval context 灌爆 input)
KGE      |  121,412  |  6,070
KAG      |  124,479  |  6,223
```

關鍵發現:
- **operator 從 0/20 → 20/20(四條全學會)** —— 模型能從 few-shot 學會那個 TTL 從未示範、
  我們自訂的複雜 `log:Condition` 套用 pattern。證明「few-shot 教得會組裝」。
- 加 operator 後四條 composite 反而**逼近滿分**(因為 operator 這個原本全 0 的維度被補上)。
  KGE 先前的 topology 殘缺(0.80)在這輪重生成也補齊了;只剩 KAG TC010 一題缺 spoke。
- token 因 few-shot 變豐富(多了 condition 區塊)整體上升 ~20–25%。
- **這是「強配方」基線**,將與架構二(weak 配方)做 CP 對決。

## Experiment Architecture 2 — weak recipe CP contest (2026-06-15)

兩個「配方」的 cost-performance 對決(spec `2026-06-13-weak-prompt-retrieval-substitution-design.md`、
plan `2026-06-15-weak-prompt-cp.md`):**Arm 1 = LLM-only 強 prompt + 強 few-shot + 無 retrieval**
vs **Arm 2 = 弱 prompt(無領域知識)+ 無 few-shot + retrieval**,外加**地板**(弱+無retrieval)。
三種 retrieval 各自獨立評,不混合。用嚴格語意評分器 + token 衡量(`compare_recipe_cp.py`)。

```text
Condition        | Parse | Composite | Tok/case | CP(comp/ktok) | evsla:hasMetric 詞名 | 官方URI
LLM-only-strong  | 100%  |  1.0000   |   5,221  |    0.192      |  (強配方)            |  20/20
LLM-only-weak    | 100%  |  0.0000   |     666  |    0.000      |   0/20               |   0/20  (地板)
GraphRag-weak    | 100%  |  0.0000   |  21,116  |    0.000      |  18/20               |   0/20
KGE-weak         | 100%  |  0.0000   |     773  |    0.000      |   8/20               |   0/20
KAG-weak         | 100%  |  0.0000   |  (未記錄)|    0.000      |   0/20               |   0/20
```
(KAG-weak token 因 crash/resume 跨輪未被 ledger 聚合,顯示 0,非真 0。)

**決定性結論:強配方完勝,四條 weak 品質全 0。**

- **retrieval 在弱配方下買不到任何品質**:floor 與三種 retrieval 的語意 composite **全 0**。
- **GraphRag-weak 是最差的 CP**:花了**每題 21,116 token(強配方的 ~4×)**換到 **0 品質**。
- 全 11 維度在所有 weak 條件下都是 0。

**為什麼 0(根因,有程式碼證據):四條 weak 全 0/20 用對官方 namespace URI。** 嚴格評分器照精確 IRI
比對,URI 錯 = 每個 triple 的 IRI 都錯 = 語意 0。而 retrieval 為何給不出正確 URI:

- **GraphRag**:`subgraph_retriever.serialize_subgraph` 把 context 壓成 **CURIE 簡寫**(`evsla:latency`),
  **完全不輸出 `@prefix` 宣告**(正確 URI 只在 `KNOWN_PREFIXES` 裡用來壓縮、從不給模型)。
  → 詞名對(18/20 `evsla:hasMetric`)但 URI 全靠猜 → 自創 `example.org/evsla#` → IRI 全錯。
- **KGE**:同樣壓 CURIE 不給 URI,且 grounding 更吵(詞名只 8/20),連命名空間風格都自創。
- **KAG**:最嚴重 —— 其 5-way solver 把 chunk **多跳合成成散文** `$content`,把精確 CURIE token 都洗成
  概念 → 詞名 0/20,全塞進自創 `tio:` 命名空間(但語意理解最深,甚至自己想出 comparisonOperator/percentile)。

**梯度規律**:retrieval 越抽象(KAG 散文合成 > KGE > GraphRag 原始 CURIE),精確詞彙流失越多。
三條 retrieval 當初都設計成「在強 prompt 旁輔助確認詞彙」,把序列化(@prefix + 組裝)留給 prompt/
few-shot;抽掉強 prompt 後全部塌回地板。

**可修性梯度(follow-up 方向)**:GraphRag 最好修(context prepend `@prefix` → URI 就齊,詞名本就對,
很可能從 0 大跳);KGE 中等;KAG 最難(要逆著其合成設計強制注入原樣 CURIE/URI)。

> CP 一句話:**目前在嚴格 TIO 正確性下,prompt-engineering 配方是唯一可行的;retrieval 在弱配方下
> 既給不出確切 URI 也給不出組裝,品質歸零,GraphRag 還白花 4× token。** 但 GraphRag 的 URI 缺口是
> 可修的序列化問題,值得當下一步驗證。

## Current Token Usage Evaluation

目前 `phase1/token_usage/compare_token_usage.txt` 結果(2026-06-13 本輪)：

```text
Experiment     | Cases | Prep total   | Avg online   | Online total | Avg calls |   Amortized @20 |  Amortized @100 | Amortized @1000
LLM-only       |    20 |            0 |      4164.65 |        83293 |      1.00 |         4164.65 |         4164.65 |         4164.65
GraphRag       |    20 |            0 |     23942.70 |       478854 |      3.00 |        23942.70 |        23942.70 |        23942.70
KGE            |    20 |        15501 |      4232.10 |        84642 |      1.00 |         5007.15 |         4387.11 |         4247.60
KAG            |    20 |            0 |      5185.30 |       103706 |      1.00 |         5185.30 |         5185.30 |         5185.30
```

目前觀察：

- **Online inference cost 最低是 LLM-only**(4,165/題);KGE(4,232/題)、KAG(5,185/題)略高;
  **GraphRag 最貴(23,943/題,每題 3 次 LLM call)≈ LLM-only 的 5.7×**,幾乎全來自把 typed-traversal
  subgraph 灌進 input。
- ⚠️ **本輪 KAG `Prep total = 0` 是因為 indexer 全部命中既有 checkpoint(0 token 重灌進新 Neo4j)**。
  從零重建 KAG KG 的 prep 成本約 **276,204 token**(前一輪 2026-06-02 實測值);amortization 要看 KAG
  時應以該 prep 計:@20≈19.7k/題、@100≈8.7k/題、@1000≈6.2k/題。本輪因 cache 命中而未付這筆。
- KGE prep(text grounding 等)約 15,501 token,攤提到 @100/@1000 後逼近其 online average(~4.2k–4.4k/題)。
- GraphRag preprocessing 為執行期 local TTL traversal,prep token = 0,但 online 平均 token 最高。

## Verification

最近一次已跑過：

```text
python3 run_all_experiments.py --eval-only
python3 -m unittest discover -v
python3 -m unittest LLM-only/test_nl_to_tio.py GraphRag/test_nl_to_tio.py KGE/KGE-based-graphrag/test_nl_to_tio.py KAG/test_nl_to_tio.py -v
```

結果：

- quality reports: 已更新到 `phase1/output_quality/`
- token reports: 已更新到 `phase1/token_usage/`
- unit tests: pass

## Experiment Architecture 3 — domain-graph GraphRAG + structure-only (2026-06-15)

重設計 GraphRAG 為 **ontology-aware domain-graph RAG**:entry-point grounding(lexical-exact + vector)
+ 只走有意義連接屬性的有界 traversal(**排除 rdf:type/subClassOf/domain/range plumbing**)+ role-scoped
封閉詞表 + 自含 `@prefix` context。新增 `structure_only` prompt profile(給組裝骨架、**抽掉全部 EVSLA 詞彙
與 namespace**,operator 也交給 retrieval 供詞 + LLM 從 NL 推方向),三條 structure-only 線共用 byte-identical
base prompt(只差 user-message 的 retrieval 區塊)。新增 20 題 hub-and-spoke 測資(TC021–040,
`test_cases_40.json`)。設計/計畫:`docs/superpowers/specs/2026-06-15-graphrag-domain-graph-redesign-design.md`、
`docs/superpowers/plans/2026-06-15-graphrag-domain-graph-redesign.md`。

四線結果(structure-only,40 題,strict `semantic_eval`,gpt-5.4):

```text
Line                       | Parse | Composite | Tok/case
LLM-only strong(天花板)    | 100%  |  0.9722   |  5,349
GraphRAG-structure         | 100%  |  0.7867   |  2,369
KGE-structure              |  95%  |  0.0051   |  8,099
LLM-only-structure(地板)   |  85%  |  0.0000   |  1,432
```

關鍵發現:

- **retrieval_information_gain = GraphRAG-structure − floor = +0.7867** —— retrieval 在「零硬寫詞彙」下
  從 0 補到 0.79,**首次成為正貢獻**。
- **replacement_gap = GraphRAG-structure − ceiling = −0.1855** —— 追到強配方上界的 **80.9%**,且只花
  **2,369 tok/題(< 強配方 5,349 的一半)**。舊版 GraphRAG ~13,500 tok/題的成本問題一併解決(~5.7×↓)。
- **KGE 仍掛(0.0051)且最貴(8,099/題)**;本輪只重設計 GraphRAG,KGE 未動,結果與先前診斷一致
  (grounding 太吵、給不出可落地官方 URI)。
- GraphRAG 各維度:metric / operator / threshold / scope / contract / precision **已追平天花板**
  (**operator 0.96** —— 歷史最難、曾 0/20 的維度,「retrieval 給詞 + LLM 從 NL 推方向」成立)。
  **缺口集中在 tenant(0.00)、time_window(0.20)、measurement_method(0.35)、topology(0.50)**。
- caveat:KGE / floor 的 0 是因吐**非官方 namespace IRI**,被精確-IRI 評分器歸零(GraphRAG 高分證明
  評分器有鑑別力,非 bug)。

報告:`phase1/phase1_{graphrag,kge,llm_only}_structure.json` + `phase1/phase1_llm_only.json`(strong 上界,
40 題)。`evaluate_ttl.py` 新增 `--test-cases` 以對 40 題 gold 評分。索引/artifacts:`GraphRag/index/`、
`KGE/KGE-based-graphrag/kge_data/`(均本機生成、未入庫)。

## Experiment Architecture 4 — canonical KGE redesign (2026-06-15)

把 KGE 從「誤用版」重設計成正統版:**text-embedding dense grounding(入口,吃同義詞)+ TransE
link-prediction 的正統用法(只排序真實 triple、永不合成)+ 共用 GraphRAG 的輸出契約**
(`resource_index`/`graph_relations`/`context_builder`)。移除三個誤用:TransE entity-cosine
neighbor expansion、predicted-triples-as-facts dump、百科 term-hint dump。設計/計畫:
`docs/superpowers/specs/2026-06-15-kge-canonical-redesign-design.md`、
`docs/superpowers/plans/2026-06-15-kge-canonical-redesign.md`。

KGE-structure 重設計前後(40 題,strict `semantic_eval`):

```text
                 | Composite | Tok/case | Parse
KGE 舊版(誤用)  |  0.0051   |  8,099   |  95%
KGE 正統版        |  0.7540   |  2,292   | 100%
```

放回四線:

```text
Line                       | Composite | Tok/case
LLM-only strong(天花板)    |  0.9722   |  5,349
GraphRAG-structure         |  0.7867   |  2,369
KGE-structure(正統)       |  0.7540   |  2,292
LLM-only-structure(地板)   |  0.0000   |  1,432
```

關鍵發現:

- **0.0051 → 0.7540(~148×),token 8,099 → 2,292(3.5×↓)**:把垃圾糾正成可用。
- **KGE vs GraphRAG = −0.0327(幾乎打平),token 還略低。**
- **為何收斂(印證 spec §11)**:重設計後 KGE 與 GraphRAG **只差「選種子機制」**(KGE = text-emb +
  TransE 真實擴張;GraphRAG = lexical + 確定性 traversal),其後「種子 → 輸出」機器、序列化、prompt
  **完全共用**。而在這小而固定的 schema 上,**到達的角色集是 schema 事實**—— ground 到任一 SLA value
  詞,hub-activation 就點亮整個角色菜單 —— 所以兩種選種子機制**殊途同歸**,分數與 token 都貼近。殘差
  來自 grounded-terms 區塊的細微差異與 KGE 的 TransE 擴張。
- **caveat**:此收斂是「小固定 schema」的性質、非普世;在更大 / 開放 / 詞彙易變的領域,grounding 對不對
  會成關鍵變數,KGE 的 embedding / 同義詞 robustness 可能拉開差距。

報告:`phase1/phase1_kge_structure.json`(已更新為正統版);`token_usage_kge.json` 含 KGE artifact 訓練的 prep token。

## Next Steps

0. **(active, 2026-06-15)** 縮 structure-only 兩條 retrieval(GraphRAG 0.79、KGE 0.75)對天花板(0.97)的
   差距,集中修兩條共同的弱維度:**tenant(0.00**;補 `evsla:Tenant` typing / `forTenant` relation,
   structure prompt 寫清楚 tenant 建模)、**time_window(~0.15)** 與 **measurement_method(~0.37)**
   (查 grounding 命中 vs prompt wiring)、**topology(~0.46**;hub/spoke 基數)。可選:wire
   KAG-structure 湊四方對照。
1. **(superseded by Architecture 3)** Weak-prompt 替代性實驗:已被 structure-only 設計取代 —— structure-only
   給組裝骨架、抽詞彙,比 all-or-nothing 的 weak prompt 更能量出 retrieval 的邊際價值。
   原設計:`docs/superpowers/specs/2026-06-13-weak-prompt-retrieval-substitution-design.md`(`b620a43`)。
1. 決定是否保留目前 `KAG` 作為 native KAG 結果，並另外新增 `kag_logical_form` variant。
2. 若要做 `kag-logical-form-grounding`，新增獨立輸出目錄與第五條 comparison line，避免和 native KAG 混在一起。
3. 將 KAG Docker compose 改成 named volumes，避免 builder KG data 因 anonymous volume 管理不清而遺失。
4. ✅ **已做(2026-06-14)**:嚴格語意評分器(`semantic_eval.py`,11 維度 graph-binding),
   見上方「Semantic Evaluator」段。後續可加:hub/spoke 名稱與基數比對(目前 topology 只驗結構)、
   weak-prompt 條件下重跑以放大 retrieval 差異、operator 權重調校。
