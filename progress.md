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

目前 `phase1/output_quality/compare_four_way.txt` 結果：

本輪完整 run notes 與 token 解讀紀錄在：

- `phase1/experiment_run_notes_2026-06-02.md`

```text
Experiment     | Cases | Parse OK   | Avg icm  | Avg ontology | Avg metric | Avg JSON nodes | Verbosity OK | Avg node ratio | Intent ID OK
LLM-only       |    20 |     95.00% |   1.0000 |       0.9806 |     1.0000 |          62.75 |      100.00% |         1.0211 |       100.00%
GraphRag       |    20 |    100.00% |   1.0000 |       0.9861 |     1.0000 |          62.75 |      100.00% |         1.0203 |       100.00%
KGE            |    20 |    100.00% |   1.0000 |       0.9944 |     1.0000 |          62.90 |      100.00% |         1.0228 |       100.00%
KAG            |    20 |    100.00% |   0.9900 |       0.9233 |     1.0000 |          61.50 |      100.00% |         0.9978 |       100.00%
```

目前觀察：

- LLM-only / GraphRAG / KGE 在 avg ICM coverage 與 avg metric coverage 上達到滿分。
- KGE 在 avg ontology coverage 上最高。
- KAG native 也完成 20/20 parse success，metric coverage 滿分，但 ontology coverage 低於 GraphRAG / KGE。
- LLM-only 仍保留為主要 baseline，代表沒有額外 ontology retrieval / graph reasoning / grounding 的情況。

## Current Token Usage Evaluation

目前 `phase1/token_usage/compare_token_usage.txt` 結果：

```text
Experiment     | Cases | Prep total   | Avg online   | Online total | Avg calls |   Amortized @20 |  Amortized @100 | Amortized @1000
LLM-only       |    20 |            0 |      5201.15 |       104023 |      1.00 |         5201.15 |         5201.15 |         5201.15
GraphRag       |    20 |            0 |     24993.35 |       499867 |      3.00 |        24993.35 |        24993.35 |        24993.35
KGE            |    20 |        15501 |     11526.70 |       230534 |      2.00 |        12301.75 |        11681.71 |        11542.20
KAG            |    20 |       276204 |      5906.35 |       118127 |      1.00 |        19716.55 |         8668.39 |         6182.55
```

目前觀察：

- Online inference cost 最低的是 LLM-only，其次是 KAG。
- KAG prep cost 很高，N=20 時 amortized cost 最高；當規模放大到 N=1000 時，KAG amortized cost 接近 online-only 成本。
- KGE prep cost 較小，amortized cost 在 N=100 / N=1000 時接近其 online average。
- GraphRAG 目前 preprocessing 為 local TTL traversal input rebuild，token prep cost 為 0，但 online retrieval/generation 平均 token 最高。

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

1. 決定是否保留目前 `KAG` 作為 native KAG 結果，並另外新增 `kag_logical_form` variant。
2. 若要做 `kag-logical-form-grounding`，新增獨立輸出目錄與第五條 comparison line，避免和 native KAG 混在一起。
3. 將 KAG Docker compose 改成 named volumes，避免 builder KG data 因 anonymous volume 管理不清而遺失。
4. 視正式實驗需要，補上 strict schema / URI hallucination / tenant placement canonicalization 等 evaluator 指標。
