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

## Next Steps

0. **(active) Weak-prompt 替代性實驗**:強 prompt 下四方品質並列頂格、evaluator 飽和,改測「retrieval 能否
   在不含領域知識的弱 prompt 下追平強-prompt 上界」。設計已定稿並 commit:
   `docs/superpowers/specs/2026-06-13-weak-prompt-retrieval-substitution-design.md`(`b620a43`)。
   下一步:進 writing-plans 拆實作計畫。
1. 決定是否保留目前 `KAG` 作為 native KAG 結果，並另外新增 `kag_logical_form` variant。
2. 若要做 `kag-logical-form-grounding`，新增獨立輸出目錄與第五條 comparison line，避免和 native KAG 混在一起。
3. 將 KAG Docker compose 改成 named volumes，避免 builder KG data 因 anonymous volume 管理不清而遺失。
4. ✅ **已做(2026-06-14)**:嚴格語意評分器(`semantic_eval.py`,11 維度 graph-binding),
   見上方「Semantic Evaluator」段。後續可加:hub/spoke 名稱與基數比對(目前 topology 只驗結構)、
   weak-prompt 條件下重跑以放大 retrieval 差異、operator 權重調校。
