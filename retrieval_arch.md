# Retrieval 架構:GraphRAG 與 KGE(structure-only 實驗線)

> 本文描述目前 **structure-only 實驗線**(`test_cases_40.json`,抽掉 EVSLA 詞彙)所使用的兩條 retrieval pipeline 的實際架構,對齊原始碼。完整逐輪實驗結果見 [`progress.md`](progress.md) Architecture 3→6;操作步驟見 [`README.md`](README.md) §4。

---

## 0. 為什麼是這個實驗線

四條 pipeline 在**強配方**(system prompt 直接手寫 EVSLA schema/詞彙 + 含詞彙 few-shot)下,語意評分早已四方飽和到 composite ≈1.0,**沒有鑑別力** —— retrieval 的語意貢獻被 prompt 天花板遮蔽。

structure-only 實驗線改問一個能量出 retrieval 邊際價值的問題:

> **當 system prompt 只給「組裝骨架」、抽掉全部 EVSLA 詞彙與 namespace 時,retrieval 能否獨力把正確詞彙補回來?**

三條 structure-only 線共用 **byte-identical** 的 `structure_only` system prompt + 同一份 sanitized skeleton few-shot(`few_shot_structure_only.json`,只有佔位符、無 EVSLA 詞彙),唯一差別是 user message 裡有沒有 retrieval context:

| 線 | retrieval context | 角色 |
|---|---|---|
| `graphrag_structure` | GraphRAG domain-graph | 受測 |
| `kge_structure` | 正統 KGE | 受測 |
| `llm_only_structure` | **無** | 地板(no-retrieval 對照) |
| `llm_only`(強配方) | n/a(full prompt) | 天花板上界 |

因為詞彙只能從 retrieval context 取得,**評分器照精確 IRI 比對** —— retrieval 給不出官方 namespace URI 的話,每個 triple 的 IRI 都錯,語意分數歸零。這讓兩條 retrieval 的差異無所遁形。

---

## 1. 共用的輸出契約(兩條 retrieval 的交集)

GraphRAG 與正統 KGE **共用同一個輸出契約**,差別只在「怎麼選種子(entry-point grounding)」。共用層全在 `GraphRag/` 底下,KGE 透過 `sys.path` 直接 import 重用:

- `resource_index.py` — 把 TTL 全 ontology 攤平成 `OntologyResource`(完整 IRI、CURIE、labels/altLabels、comment、`role_class` 角色分類)。
- `graph_relations.py` — 有界 connective traversal + closed-world 角色展開 + ontology 慣例讀取。
- `context_builder.py` — `serialize_context(...)` 把結果序列化成自含 `@prefix` 的 LLM context。

`serialize_context` 產出的 context 固定有四個區塊:

```text
### Canonical prefixes
evsla: <http://tio.models.tmforum.org/tio/v3.6.0/EnterpriseVpnSlaOntology/>
icm:   <...>   quan: <...>   ...

### Grounded terms (NL concept -> ontology term)
- evsla:latency (evsla:Metric ...) -- <comment 前 160 字>
- ...

### Connective relations (how an SLA expectation wires together)
- evsla:SlaExpectation evsla:hasMetric -> evsla:Metric
- evsla:HubAndSpokeTopology evsla:hasSpoke -> evsla:SpokeSite
- ...

### Closed vocabulary per reached role (pick one per slot)
- Statistic: evsla:average, evsla:percentile95, ...
- MeasurementMethod: evsla:twamp, evsla:activeMeasurement, ...
- ...

### Conventions (apply when the NL gives no explicit cue)
- Measurement method default per metric:
  - evsla:latency -> evsla:twamp
  - evsla:guaranteedBandwidth -> evsla:activeMeasurement
- Time window default: evsla:fiveMinuteWindow
  - if NL mentions 「每小時」 use evsla:oneHourWindow
  - if NL mentions 「月度」 use evsla:oneMonthWindow
```

**關鍵設計**:`@prefix` 完整宣告**永遠**隨 context 一起給(舊版只給 CURIE 簡寫、不給 URI,是 weak/structure-only 全 0 的根因)。詞彙是 **role-scoped 封閉詞表**(每個 slot 只能從清單挑一個),而不是讓模型自由發揮。

---

## 2. GraphRAG 架構

`GraphRag/` —— **ontology-aware domain-graph RAG**。執行期直接讀 `TM Forum Intent Ontology/*.ttl`(rdflib),改 TTL 免重建。

```text
NL intent
  → entry-point grounding (lexical-exact + vector)        [subgraph_retriever.ground_query]
  → bounded connective traversal (排除 plumbing)           [graph_relations.traverse_connective]
  → closed-world 角色展開 (碰到 metric → 點亮整份 SLA 角色)  [traverse_connective 後半]
  → role-scoped 封閉詞表 + conventions + 自含 @prefix       [context_builder.serialize_context]
  → LLM 生成 TIO Turtle                                    [nl_to_tio.generate_turtle_code]
```

### 2.1 Entry-point grounding(混合 lexical + vector)

`subgraph_retriever.ground_query` 對每個 ontology resource 算混合分數:

```
combined = 0.45 · lexical + 0.55 · vector        (vector < 0.20 視為 0)
```

- **lexical**(`_lexical`):query 與 resource 的 labels/altLabels/CURIE local-name 做 token 比對(精確命中 = 1.0,子集 = 0.8,部分交集按比例)。
- **vector**:query text embedding 與 **offline resource index**(`GraphRag/index/resource_embeddings.npy`)的 cosine。index 由 `build_index.py` 預先建立 —— 對每個 resource 的 `labels + altLabels + comment` 取 embedding(`text-embedding-3-small`)。沒有 index 時 grounding 退化為 lexical-only。

取 top-12 grounded resources 當種子。

### 2.2 有界 connective traversal(排除 plumbing)

`graph_relations.traverse_connective` **只走有意義的連接屬性**(`CONNECTIVE_PROPERTIES`):

```
hasMetric, hasThreshold, hasStatistic, hasScope, hasMeasurementMethod,
hasTimeWindow, hasHub, hasSpoke, forTenant
```

**刻意排除** `rdf:type` / `rdfs:subClassOf` / `rdfs:domain` / `rdfs:range` 這類 schema plumbing —— 它們會把無關的本體骨架灌進 context。種子若命中某個 connective property 的 domain/range(或其 instance),該 property 的 hub 就被啟用,emit `(domain, prop, range)` 關係並依 range 標記「reached role」。

### 2.3 Closed-world 角色展開(EVSLA 的封閉世界契約)

只要 traversal 碰到 **Metric**(代表存在一個 SLA expectation),就**保證**供出整份 SLA 角色,不靠 traversal 是否剛好走到:

```python
if "Metric" in reached:
    reached.update({"Tenant", "MeasurementMethod", "TimeWindow",
                    "HubSite", "SpokeSite", "HubAndSpokeTopology"})
```

`HubSite` / `SpokeSite` / `Tenant` 在 ontology 裡**沒有 instance**(它們是給 case 專屬節點打型別用的 class),所以額外 emit `forTenant` / `hasHub` / `hasSpoke` 的 wiring 關係,讓 **class IRI** 進 context。這就是 Architecture 5 把 tenant/topology 從 0 拉到 ~1.0 的機制。

### 2.4 Conventions(ontology 內建慣例)

`extract_conventions` 從 EVSLA TTL 讀出領域慣例(編在 ontology、非寫死在 code):

- `evsla:defaultMeasurementMethod`:per-metric 預設量測方法(latency/packetLoss→twamp、guaranteedBandwidth→activeMeasurement)。
- `evsla:isDefaultTimeWindow`:預設時間窗(fiveMinuteWindow)。
- window instance 的中文 `rdfs:label@zh`:NL 觸發詞 →window IRI 對應(「每小時」→oneHourWindow)。

這補上了 time_window / measurement_method 兩個弱維度(NL 常常不明說量測方法)。

---

## 3. KGE 架構(正統版)

`KGE/KGE-based-graphrag/` —— **正統 KGE**:用 TransE link-prediction **排序真實 triple**,**永不合成** triple 或 entity。與舊「誤用版」(TransE entity-cosine 鄰居展開、predicted-triples-as-facts dump、百科 term-hint dump)決裂。

```text
NL intent
  → text-embedding dense grounding (entry-point, 吃同義詞)   [kge.select.text_ground]
  → TransE 真實-triple 擴張 (只排序、不合成)                  [kge.select.transe_expand]
  → 共用 GraphRAG 輸出契約 (assemble_context)               [kge.select.assemble_context]
  → LLM 生成 TIO Turtle                                     [nl_to_tio]
```

**KGE 與 GraphRAG 的唯一差別就是「選種子機制」**;`assemble_context` 拿到 grounded URI 後,走的是和 GraphRAG `build_retrieval_context` **完全相同**的 `traverse_connective` / `closed_vocab_for_reached_roles` / `extract_conventions` / `serialize_context`。

### 3.1 Offline artifacts(`kge.train`)

`python -m kge.train` 從 ontology TTL 一次產出(寫到 `kge_data/`,已 gitignore):

- **TransE entity / relation embedding**(PyKEEN,預設 dim=128、80 epochs),L2-normalize。
- **per-entity text embedding**(`text-embedding-3-small`,對每個 entity 的描述文字),L2-normalize 供 cosine。
- `triples.tsv`:從 TTL 抽出的真實 (h, r, t),供 link-prediction 排序用。

TTL 變更後需 `python -m kge.train` 重訓(GraphRAG 免重建,因執行期讀 TTL)。

### 3.2 Dense grounding(`text_ground`)

query text embedding 與 entity text embedding 矩陣相乘取 top-8。這是 **dense/語意** 入口,能吃 lexical 比不到的同義詞 / 非字面 mention。

### 3.3 TransE 真實-triple 擴張(`transe_expand`)

對每個種子,掃過 `triples.tsv` 中**含該種子的真實 triple**,用 TransE 分數 `-‖h + r − t‖`(越大越合理)排序,取 top-8 triple,回傳其中**真實存在**的鄰居 entity。

> 這是 TransE link-prediction 的正統用法:**對既有 triple 評分排序,而不是憑 embedding 幻想新 triple**。種子 + 擴張的 URI 一起送進 `assemble_context`。

---

## 4. 為什麼兩條會收斂

重設計後 KGE 與 GraphRAG **只差選種子機制**(KGE = text-embedding + TransE 真實擴張;GraphRAG = lexical + 確定性 traversal),其後「種子 → 輸出」的 traversal、序列化、prompt **完全共用**。

而在 EVSLA 這個**小而固定的 schema** 上,**到達的角色集是 schema 事實** —— ground 到任一個 SLA value 詞,§2.3 的 hub-activation 就點亮整份角色菜單。所以兩種選種子機制**殊途同歸**,composite 與 token 都貼得很近。

> **caveat**:此收斂是「小固定 schema」的性質、非普世。在更大 / 開放 / 詞彙易變的領域,grounding 對不對會成關鍵變數,KGE 的 embedding / 同義詞 robustness 可能拉開差距。

---

## 5. 結果(Architecture 6,2026-06-17 正式重跑)

structure-only,`test_cases_40.json`,Azure `gpt-5.4`,embedding `text-embedding-3-small`,strict `semantic_eval`(11 維 graph-binding composite)。

```text
Line                       | Parse | Composite | Avg online tok | Prep tok
LLM-only strong(天花板)    | 100%  |  0.9738   |     5,354      |      0
GraphRAG-structure         | 100%  |  0.9746   |     2,718      | 14,365
KGE-structure(正統)       | 100%  |  0.9778   |     2,722      | 15,555
LLM-only-structure(地板)   |  95%  |  0.0000   |     1,532      |      0
```

逐維度(11 維):

```text
Dimension          | LLM ceiling | GraphRAG | KGE
metric             |    1.00     |  1.00    | 1.00
threshold          |    0.96     |  0.96    | 0.96
statistic          |    0.99     |  0.92    | 0.92
scope              |    0.88     |  0.91    | 0.96
measurement_method |    0.97     |  0.97    | 0.97
time_window        |    0.90     |  1.00    | 1.00
operator           |    1.00     |  0.96    | 0.96
tenant             |    1.00     |  1.00    | 0.97
topology           |    1.00     |  1.00    | 1.00
contract           |    1.00     |  1.00    | 1.00
precision          |    1.00     |  1.00    | 1.00
```

**結論**:

- **KGE 0.9778 ≳ GraphRAG 0.9746 ≳ LLM ceiling 0.9738** —— 兩條 retrieval 都達到/略超天花板品質。
- **online token 約 ceiling 的 51%**(GraphRAG 2,718、KGE 2,722 vs ceiling 5,354);prep token 很小,攤到 @100 後仍約 2.86k/2.88k per case,明顯低於 ceiling。
- floor parse 可達 95% 但 composite 仍 0,證明「可 parse 的 Turtle」不等於 TIO 語意正確。
- 演進路徑:GraphRAG 0.79(Arch 3)→ KGE 正統化 0.75(Arch 4)→ 四維度 grounding 兩條皆 ~0.98(Arch 5)→ Azure 正式重跑 ~0.97(Arch 6)。

---

## 6. 程式對照速查

| 階段 | GraphRAG | KGE |
|---|---|---|
| Entry-point grounding | `subgraph_retriever.ground_query`(lexical+vector) | `kge.select.text_ground`(text-emb)+ `transe_expand`(TransE 真實擴張) |
| Offline artifacts | `build_index.py` → `GraphRag/index/` | `kge.train` → `kge_data/` |
| Traversal / 角色展開 | `graph_relations.traverse_connective` | (共用)`graph_relations.traverse_connective` |
| 慣例 | `graph_relations.extract_conventions` | (共用) |
| Context 序列化 | `context_builder.serialize_context` | (共用)`kge.select.assemble_context` |
| 生成 | `GraphRag/nl_to_tio.py` | `KGE/KGE-based-graphrag/nl_to_tio.py` |
| 共用 prompt | `evsla_prompt.build_evsla_system_prompt(..., profile="structure_only")` | (同一支) |

跑法見 [`README.md`](README.md) §4。
