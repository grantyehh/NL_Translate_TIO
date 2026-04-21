# TIO 轉譯標準草案

本文件是為本專案的 `NL -> TIO Turtle` 生成流程所整理的工作標準。
目的不是完整重述 TM Forum 全部 ontology，而是定義：

- 目前這個 repo 應優先產生什麼粒度的 Turtle
- 哪些結構是核心且必須穩定
- 哪些高粒度 pattern 可以逐步導入
- 哪些做法目前不應直接當成通則

本文件適用於：

- `LLM-only/`
- `GraphRag/`
- `KGE/KGE-based-graphrag/`

---

## 1. 目標

本專案的輸出目標不是最粗略的骨架，也不是每題都強制 fully formal 的極細粒度表示。

目前建議採用的標準是：

- 以 **中高粒度** 的 TIO 表示為主
- 核心語意必須結構化
- 補充語意可保留在 `rdfs:comment`
- 高粒度函式型 pattern 僅在適合題型時使用

一句話原則：

> 能穩定結構化的核心語意，優先結構化；沒有穩定模板的次要語意，暫時保留在 `rdfs:comment`。

---

## 2. 專案現況與約束

本標準需要同時對齊本專案現有的三個面向：

### 2.1 生成器現況

目前 `GraphRag/nl_to_tio.py`、`LLM-only/nl_to_tio.py`、`KGE/.../nl_to_tio.py` 的 prompt 都要求：

- 使用官方 TIO namespace
- 輸出純 Turtle
- 以合法 class/property 為主

### 2.2 Phase-1 evaluator 現況

`evaluate_ttl.py` 目前主要檢查：

- Turtle 是否可 parse
- class/property 是否存在於 `TM Forum Intent Ontology/`
- `expected_tio_elements` 是否被顯式使用

因此若核心語意只存在於 `rdfs:comment`，常會降低 `expected_coverage_ratio`。

### 2.3 Golden / Phase-2 方向

`goldens/` 代表的是更接近人工審查與語意比對的方向。它不要求逐字相同，但會關注：

- 關鍵元素是否存在
- 關鍵 triple pattern 是否存在
- 關鍵值、單位、比較方向是否被正確表達

因此本專案的理想輸出，應該逐步從「合法骨架」提升到「關鍵語意可檢查」。

---

## 3. 核心規則

本節是目前專案中 **所有題型都應盡量遵守** 的規則。

### 3.1 Prefix 規則

所有 TIO 詞彙必須使用官方 prefix 與官方 IRI。

最低常用集合：

- `icm:` Intent Common Model
- `log:` Logical Operators
- `quan:` Quantity Ontology
- `met:` Metrics And Observations
- `rdfs:`
- `rdf:`

只有在實際使用到某個 module 的詞彙時，才宣告該 prefix。

### 3.2 Instance URI 規則

實例節點可使用 `example.org` base，但必須：

- 與官方詞彙 namespace 分離
- 包含 testcase ID 或其他可追蹤識別

建議格式：

```turtle
<http://example.org/tio-instance/TC002/intent>
<http://example.org/tio-instance/TC002/exp-throughput>
<http://example.org/tio-instance/TC002/target>
```

### 3.3 Intent 規則

每一題都應有一個頂層 `icm:Intent` 實例。

最小形式：

```turtle
<.../intent> a icm:Intent .
```

### 3.4 Target 規則

每個 requirement 都必須有明確 target，或能清楚對應到某個 target。

最小形式：

```turtle
<.../target> a icm:Target .
```

如果 target 的精細成員結構尚未有穩定模板，可先用 `rdfs:comment` 描述。

例如：

```turtle
<.../target> a icm:Target ;
  rdfs:comment "Gaming users."@en .
```

### 3.5 Expectation 規則

每個核心 requirement 都應實例化為 expectation。

優先使用：

- `icm:DeliveryExpectation`
- `icm:PropertyExpectation`

若題型暫時不適合細分，可退回：

- `icm:Expectation`

Expectation 應透過 `icm:target` 與 target 綁定：

```turtle
<.../exp> a icm:PropertyExpectation ;
  icm:target <.../target> .
```

### 3.6 多 requirement 拆分規則

若自然語言中包含多個核心需求，應拆成多個 expectation，不應把多個核心約束全部塞在單一 comment。

例如：

- throughput 與 latency 分成兩個 expectation
- latency 與 jitter 分成兩個 expectation
- property requirement 與 delivery requirement 分成兩個 expectation

### 3.7 Context / Condition 規則

以下語意應優先建成獨立節點，而非只寫在 comment：

- 時間窗口
- 事件發生中
- 門檻觸發條件
- 條件式需求

建議使用：

- `icm:Context`
- `log:Condition`

例如：

```turtle
<.../intent> a icm:Intent ;
  icm:context <.../context> .

<.../context> a icm:Context ;
  rdfs:comment "Weekday working hours 08:00-18:00."@en .
```

或：

```turtle
<.../condition> a log:Condition ;
  rdfs:comment "Base station load is greater than 80%."@en .
```

### 3.8 Comment 使用規則

`rdfs:comment` 是補充工具，不是核心語意的唯一承載位置。

適合放在 comment 的資訊：

- target 的自然語言描述
- 補充場景說明
- 暫時無穩定 formal pattern 的細節

不應只放在 comment 的資訊：

- 多 requirement 的拆分
- 是否有 context / condition
- expectation 類型
- target 對象
- 明確的高頻性能門檻（若已有穩定模板）

---

## 4. 進階模式

本節列出可逐步導入的高粒度 pattern。
這些 pattern **不是所有題目都必須使用**，只有在題型適合、few-shot 已教過、prompt 已明確要求時才使用。

### 4.1 值比較模式

適用題型：

- latency `<`
- throughput `>`
- availability `>=`
- load threshold `>`

建議使用：

- `quan:greater`
- `quan:smaller`
- `quan:atLeast`
- `quan:atMost`

建議與：

- `quan:quantity`
- `met:lastValue`
- `icm:valuesOfTargetProperty`

搭配使用。

### 4.2 Metric / Property 取值模式

對於「某 target 的某個 property 值」這類題型，應優先考慮：

- `icm:valuesOfTargetProperty`

這對本專案尤其重要，因為 phase-1 的某些 testcase 直接要求它出現。

若要進一步 formalize，可在穩定題型中考慮：

- `met:lastValue`

但只有在該 pattern 已有明確模板時才使用。

### 4.3 邏輯組合模式

適用題型：

- 且 / 同時滿足
- 多條件 conjunction
- 多 expectation 聚合

可選使用：

- `log:allOf`

但注意：

- `log:allOf` 目前是高粒度 pattern，不是所有多 requirement 題的必備結構
- 若使用，必須有清楚且一致的節點角色定義

### 4.4 條件觸發模式

適用題型：

- 如果 load > 80%，則限制某流量
- 若回程延遲 > 15ms，則降低優先權

最低要求：

- 建立 `log:Condition`
- 建立對應 expectation

進階要求：

- 將 threshold / operator / unit 顯式化

### 4.5 題型模板優先於自由生成

若要導入進階模式，應優先使用「題型模板」而非讓模型自由選擇 pattern。

建議至少建立以下模板：

- `single_delivery`
- `single_property_threshold`
- `multi_property_same_target`
- `contextual_requirement`
- `conditional_requirement`

---

## 5. 題型選擇規則

本節定義「什麼題型，至少應長成什麼樣子」。

### 5.1 Delivery 題

例如：

- 建立 5G slice
- 新增 coverage
- 提供專用服務

最低要求：

- `icm:Intent`
- `icm:DeliveryExpectation`
- `icm:Target`
- `icm:target`

### 5.2 單一 Property 門檻題

例如：

- latency < 5ms
- availability >= 99.99%
- throughput >= 500Mbps

最低要求：

- `icm:PropertyExpectation`
- `icm:Target`
- `icm:target`

優先強化：

- 顯式表達 property/value/operator/unit

### 5.3 多 Property 同目標題

例如：

- throughput > 100Mbps 且 latency < 10ms
- latency < 10ms 且 jitter < 2ms

最低要求：

- 一個 target
- 多個 `icm:PropertyExpectation`
- 每個 expectation 都連到同一 target

高粒度可選：

- `log:allOf`
- `icm:valuesOfTargetProperty`
- `met:lastValue`
- `quan:* comparison`

### 5.4 Context 題

例如：

- 平日 08:00-18:00
- 遠距維運期間

最低要求：

- `icm:Intent`
- `icm:Context`
- `icm:context`

### 5.5 Conditional 題

例如：

- 如果基站負載超過 80%，則限制頻寬

最低要求：

- `icm:Intent`
- `log:Condition`
- `icm:PropertyExpectation`
- `icm:Target`

高粒度可選：

- 顯式 threshold / operator / unit

---

## 6. 必須、優先、可選

### 6.1 必須

- 使用官方 TIO prefix
- 建立 `icm:Intent`
- 建立 target
- 建立 expectation
- expectation 連到 target
- 題目需要時建立 `Context` 或 `Condition`
- 避免 hallucinated predicate

### 6.2 優先

- 多 requirement 拆成多個 expectation
- 核心 threshold/value/unit 不只寫在 comment
- 單一題型使用一致 pattern
- 使用 phase-1 testcase 指定的關鍵元素

### 6.3 可選高粒度

- `log:allOf`
- `met:lastValue`
- `quan:greater/smaller/atLeast/atMost`
- 更細的 function-style comparison pattern

---

## 7. 目前不應直接當成通則的做法

以下做法目前可研究、可局部實驗，但不應直接當成專案統一標準：

- 把 `rdfs:member` 當作 target 的預設表達法
- 假設所有 property 題都必須使用 `met:lastValue`
- 假設所有多 requirement 題都必須使用 `log:allOf`
- 讓模型自由選擇高粒度 function pattern 而不經題型模板約束
- 只因 ontology 中存在某詞，就在沒有穩定模板時直接納入生成主流程

---

## 8. 與評估對齊的實務建議

### 8.1 對 Phase-1

若 testcase 明確要求某個元素，應優先顯式用出來。

例如：

- `icm:valuesOfTargetProperty`

即使存在其他高粒度合法寫法，也應考慮 phase-1 coverage 是否會因此下降。

### 8.2 對 Golden / Phase-2

生成不必逐字貼近 golden turtle，但應確保：

- 核心節點存在
- 核心關係存在
- 核心值、單位、比較方向有被表達

### 8.3 對 Few-shot

few-shot 應分層：

- 骨架型
- 中粒度型
- 高粒度型

並依題型動態選取，不應整包固定灌入。

---

## 9. 建議的實作方向

若本專案要逐步提升粒度，建議依序進行：

1. 先補 `single_property_threshold`、`multi_property_same_target`、`conditional_requirement` 三類模板
2. 更新 few-shot，使其覆蓋中高粒度 pattern
3. 更新 prompt，明確區分「必須結構化」與「可留 comment」
4. 再逐步導入 `log` / `quan` / `met` 的高粒度模式
5. 最後補 phase-2 evaluator，使其能比較 operator/value/unit 等語意

---

## 10. 總結

本專案的標準方向不是：

- 只產生最粗的骨架
- 或每題都追求最複雜的 fully formal 表達

而是：

- 以中高粒度為主
- 先確保核心語意穩定結構化
- 再逐步擴充高粒度函式型 pattern

這樣才能同時兼顧：

- 生成穩定性
- evaluator 對齊
- 後續工程可用性
- 向更高粒度 TIO 建模演進的可能性
