# Progress Report: GraphRAG Typed Traversal Experiment

Conclusion recorded at: 2026-05-19 22:55:21 CST

## Current Status

目前 `graphrag-typed-traversal` 分支已完成 GraphRAG pipeline 的替代實作，並已重新產生 `jsonld_outputs/graphrag/TC001.jsonld` 到 `TC020.jsonld`。新版 GraphRAG 不再使用 Microsoft GraphRAG CLI 的 document-centric retrieval，而是直接使用 `TM Forum Intent Ontology/*.ttl` 作為 RDF graph，根據 user query 抽出的 seed terms 做 typed traversal，取回 query-specific ontology subgraph，再交給 LLM 生成 TIO JSON-LD。

目前已完成並驗證：

- `GraphRag/ontology_graph.py`: 載入 TTL、建立 label/comment/type index、執行 typed BFS。
- `GraphRag/subgraph_retriever.py`: seed extraction、seed-to-URI grounding、subgraph serialization。
- `GraphRag/nl_to_tio.py`: 改用 typed RDF traversal context 取代 Microsoft GraphRAG CLI context。
- `jsonld_outputs/graphrag/*.jsonld`: 已用新版流程重新產生 20 題輸出。
- `phase1/phase1_graphrag.json`: 已用 evaluator 重算新版 GraphRAG 結果。

## Why This Change Matters

原本的 Microsoft GraphRAG pipeline 比較適合大量非結構化文件的問答場景。它會把文件切成 chunks/text units，抽 entity 和 relationship，建立 community reports，再透過 local/global search 回傳文字型 context 給 LLM。

但本專案的任務不是一般文件問答，而是：

```text
Natural language intent -> TIO JSON-LD
```

而且我們已經有正式的 `TM Forum Intent Ontology` TTL 檔。也就是說，知識來源本身已經是結構化 RDF ontology，不需要先經過 Microsoft GraphRAG 的文字 chunk 和 community summary 流程。原本使用 Microsoft GraphRAG 時，LLM 看到的 context 容易變成文字摘要或段落，可能反而弱化 URI、class/property、domain/range 等 ontology 結構訊號，進而讓輸出接近 LLM-only baseline。

新版做法改成直接使用 ontology graph：

```text
user query
-> extract seed terms
-> ground seed terms to ontology URIs
-> 2-hop typed traversal over RDF graph
-> serialize triples + comments
-> LLM generates TIO JSON-LD
```

這讓 LLM 看到的是更接近任務需求的結構化 context，例如 `evsla:latency`、`evsla:p95`、`evsla:twamp`、`evsla:hubToAllSpokes`、`evsla:SlaExpectation` 等實際 ontology terms，而不是較鬆散的文字段落。

## Evaluation Result

使用 `evaluate_jsonld.py graphrag` 評估新版 GraphRAG 後，結果如下：

```text
cases: 20
parse_ok: 20/20 (100.0%)
expected_tio_elements_avg: 100.0%
ontology_terms_avg: 98.9%
performance_metrics_avg: 100.0%
```

四條線目前的 phase1 對比：

```text
Experiment     | Parse OK | Avg ICM | Avg ontology | Avg metric | Avg JSON nodes
LLM-only       |  95.00%  | 0.8975  | 0.0000       | 0.0000     | 39.50
GraphRag       | 100.00%  | 1.0000  | 0.9889       | 1.0000     | 62.65
KGE-hybrid     |  95.00%  | 0.8650  | 0.0000       | 0.0000     | 38.40
KAG            |  80.00%  | 0.9000  | 0.8861       | 0.9000     | 54.60
```

目前新版 GraphRAG 在 evaluator 上是四條線中表現最好的：

- Parse success rate: `100%`
- ICM coverage: `1.0000`
- Ontology term coverage: `0.9889`
- Performance metric coverage: `1.0000`

## Interpretation

初步結果顯示，對於本專案這種 ontology-to-JSON-LD 生成任務，直接使用 RDF ontology 做 typed subgraph retrieval，比原本透過 Microsoft GraphRAG CLI 產生文字 context 更有效。

可能原因是 Microsoft GraphRAG 的 document-centric pipeline 會把已經結構化的 ontology 轉成較間接的文字 retrieval context，導致 LLM 不一定能穩定使用正確的 TIO URI 和 schema structure。新版 typed traversal 則直接暴露 query-relevant triples 和 comments，讓 LLM 更容易對齊到正確的 ontology terms，因此在 URI 使用率、schema/ICM coverage 和 performance metric coverage 上都有明顯提升。

需要注意的是，目前只有 GraphRAG typed traversal 是最新重新跑出的結果；其他 `LLM-only`、`KGE-hybrid`、`KAG` 報告來自 repo 既有 phase1 檔案。若要作為正式實驗結論，建議後續用同一組模型設定、同一時間重新跑四條 pipeline，再產生最終比較報告。

## Next Steps

1. 保留 `graphrag-typed-traversal` 作為 GraphRAG 改良版實驗分支。
2. 在正式報告前，重新跑 `LLM-only`、`KGE-hybrid`、`KAG`，確保四條線比較條件一致。
3. 後續可分別開新 branch 實作：
   - `kge-link-prediction`
   - `kag-logical-form-grounding`
4. 最後再比較三種改良版 retrieval/grounding 方法是否都優於 baseline。
