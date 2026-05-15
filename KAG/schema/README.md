# TIO_EVSLA KAG Schema(初版草稿)

## 範圍

把 TM Forum TIO 與 EVSLA 擴充 ontology **跟 `test_cases_20.json` 實際會用到** 的部分,翻成 OpenSPG KAG 的 schema DSL。

| 翻過來的 TTL 範圍 | 來源檔 |
|---|---|
| EVSLA 全部 class 與 property | `tio-agent/ttls/EnterpriseVpnSlaOntology.ttl` |
| ICM 抽象基底(Intent / PropertyExpectation / Target / Context) | `TM Forum Intent Ontology/IntentCommonModel.ttl`(只取對應結構,沒寫獨立 entity) |
| Quantity(value + unit) | `TM Forum Intent Ontology/QuantityOntology.ttl`(flatten 進 SlaExpectation) |

統計:**7 個 ConceptType + 8 個 EntityType + 約 50 個 properties/relations**。

## 主要設計取捨

1. **KAG 沒 subClassOf**:`evsla:EnterpriseVpnSlaIntent subClassOf icm:Intent` 在 KAG 變成 EntityType 上的 `tioType` 屬性帶 IRI 字串,下游 JSON-LD 輸出時用。
2. **TTL instance → KAG ConceptType hyponym**:`evsla:p95 a evsla:Statistic` 這類列舉,KAG 改用 ConceptType + `IND#hasStatistic` 分類索引,讓 retrieval 可命中。
3. **Nested struct flatten**:`quan:Quantity {value, unit}` 拆成 `thresholdValue: Float` + `thresholdUnit: Text`(KAG schema 不支援 nested type)。
4. **xsd:boolean → Text**:`evsla:appliesPerSpoke` 在 KAG 沒原生 boolean,用 `"true"/"false"` 字串。
5. **Index 策略**:
   - `name`、`description`、`location`、`nlIntent`、`industry` → `TextAndVector`(語意搜尋會打到)
   - ID / enum 字串 / `tioType` → 預設 `Text`(只走關鍵字)
   - 數值欄位 → 無 index(等於底層 attribute,solver 用 query 過濾)

## 刻意不做的部分

| 略過的 TTL | 理由 |
|---|---|
| `icm:DeliveryExpectation` / `icm:ReportingExpectation` | test_cases_20 全是 PropertyExpectation |
| `icm:*Report` 系列 | 監控回報路徑屬 Phase B 監控閉環 |
| `log:Condition` / `log:allOf` | 20 題裡沒條件式 intent |
| `quan:` 完整 unit ontology | flatten 後 2 欄夠用 |
| `met:lastValue` / `met:metric` 完整路徑 | 用 `IND#hasMetric` → `TIO_MetricType` 替代 |
| `IntentManagementOntology` / `IntentSpecification` / `IntentValidity` | lifecycle / spec / validity 是 Phase B+ 範圍 |

12 個 TM Forum TTL 中,目前只取 3 個(ICM / Quantity / Metrics)+ EVSLA 擴充;其餘 9 個(IntentValidity / IntentSpecification / IntentManagement / LogicalOperators / MathFunctions / SetOperators / IntentGuarantee / IntentProbing / PreferenceOfHandlingOutcomes / Utility / ProposalBestIntent / FunctionOntology)在當前測試集裡用不到,Phase C 後若有需要再補。

## 已知未驗證項

- **`IND#` 在 EVSLA 多 metric 並列場景的命中表現**:test_cases TC011~ 之後可能有同一 SlaExpectation 多 metric 的題,目前模型每個 expectation 只允許 1 個 `IND#hasMetric`,要看 retrieval 還能不能對齊。
- **`hasExpectation` MultiValue 是否正確語法**:從 riskmining example 抄的 `constraint: MultiValue`,還沒在 KAG schema commit 時驗過。
- **`TIO_SlaTier` 列舉成員 basic / standard / gold 的來源**:在 EVSLA TTL **沒有定義**,是從 POC ground_truth 借過來對齊彥廷 DSL;若團隊決定 tier 不是 evsla 的事,這個 ConceptType 可拿掉。

## 下一步(在 docker stack 跑起來之後)

1. `knext schema commit` 把這個 schema 推到 OpenSPG server,看 parse error
2. 在 Neo4j browser(`localhost:7474`)直接看 schema 是否建好對應 label
3. 寫 `seed_topology.py` 把 5 個測試租戶(星河銀行 / 遠東製造 / 宏海物流 / 康健醫療 / 晨星零售)的 Tenant + Service + Hub + Spoke 餵進去當 grounding 資料
4. builder 走 KAG 自動抽取,把 `EnterpriseVpnSlaOntology.ttl` 與 few-shot example 當文件來源
5. `nl_to_tio.py` 接 kg-solver 取 retrieval context → LLM 生 JSON-LD
