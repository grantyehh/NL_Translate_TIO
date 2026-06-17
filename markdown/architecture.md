# NL to TIO 實驗及方法評估

> 簡報大綱(條列為主,實作時把每條展開成 slide;標 [圖] 的優先用圖表勝過文字)。
> 數據以 [`progress.md`](progress.md) Architecture 6 為準;架構細節見 [`retrieval_arch.md`](retrieval_arch.md)、評估器見 [`evaluator.md`](evaluator.md)。

## 0. 開場
* 標題 / 講者 / 一句話主旨:**用 retrieval 取代 prompt-engineering,省一半 token 仍達到純 LLM 的品質**
* Agenda(本簡報七個段落)
* Setup 一行(reproducibility):Azure `gpt-5.4` + `text-embedding-3-small`,40 題測資(`test_cases_40`),strict `semantic_eval` 評分

## 1. 前述
* 為什麼需要 TIO(意圖驅動網路:NL 意圖 → 機器可消費的標準化 intent)
* [圖] 一個**具體 NL → TIO Turtle 範例**(一句中文 SLA 意圖 → 一小段 Turtle),讓聽眾秒懂產物長什麼樣
* 這個實驗的目的:研究 **retrieval 方法相對於單純使用 LLM 的優勢**
* Motivation / 問題:在強 prompt 下,schema 與詞彙都被手寫進去,**量不出 retrieval 的價值**(見下節)

## 2. 核心實驗設計:structure-only(整場的靈魂)
* 強配方(strong prompt + 含詞彙 few-shot):四條品質都飽和到 composite ~1.0 → **沒有鑑別力**
* 解法:把 EVSLA 詞彙與 namespace **從 prompt 抽掉**,只留「組裝骨架」(structure-only profile)
  * 三條 structure-only 線共用 **byte-identical** 的 system prompt + 同一份 sanitized skeleton few-shot(無詞彙)
  * 唯一變因 = user message 裡有沒有 retrieval context
* 這樣才能公平量出「retrieval 能否獨力把正確詞彙補回來」

## 3. 四條實驗線簡述
* [圖] 天花板 / 地板框架:
  * **LLM-only 強配方 = 天花板**(full prompt,品質上界)
  * **GraphRAG-structure / KGE-structure = 受測的兩條 retrieval**
  * **LLM-only-structure = 地板**(structure prompt 但無 retrieval → composite **0**)
  * 地板掉到 0 → 證明「retrieval 確實在做事」
* 基礎配置差異要明確寫出:strong(天花板,含詞彙)vs **structure_only**(三條共用 skeleton few-shot,抽詞彙)
  * 註:舊的「weak 配方」已被 structure-only 取代,本場不談 weak
* 測資架構介紹:hub-and-spoke 拓樸(TC021–040),涵蓋 tenant / 多 spoke 站點
* KAG 範圍說明:KAG 為另一條 native builder + solver 路線,**不在本 structure-only 比較內**(避免聽眾追問)

## 4. 自創 GraphRAG 架構設計
* [圖] 為什麼**不適合用 Microsoft GraphRAG**:document-centric、把散文 chunk 多跳合成、給不出精確官方 IRI(URI 全靠猜 → 語意歸零)
* [圖] 四步流程(根據 retrieval_arch.md):
  1. entry-point grounding(lexical-exact + vector 混合)
  2. 有界 connective traversal(**只走有意義屬性,排除 rdf:type / subClassOf / domain / range plumbing**)
  3. closed-world 角色展開(碰到 metric → 點亮整份 SLA 角色:tenant / method / window / hub / spoke)
  4. role-scoped 封閉詞表 + ontology 慣例 + **自含 `@prefix` context**
* 原則:用圖大於用文字,簡單扼要,但「排除 plumbing」「自含 @prefix」這兩個重點不可省

## 5. KGE 架構設計
* [圖] 流程(根據 retrieval_arch.md):text-embedding dense grounding(吃同義詞)→ TransE link-prediction → 共用 GraphRAG 輸出契約
* 重點:**正統 KGE 用法** — TransE 只**排序真實 triple、永不合成** triple/entity(與舊「誤用版」決裂)
* [圖] **兩條為何收斂**(深度賣點):GraphRAG 與 KGE **只差「選種子機制」**,其後 traversal / 序列化 / prompt 完全共用;在小而固定的 schema 上殊途同歸
  * caveat:此收斂是「小固定 schema」的性質,大 / 開放 / 詞彙易變的領域可能拉開差距
* (可選)四維度 grounding:tenant / time_window / measurement_method / topology 靠 **ontology 內建慣例** 補齊,把兩條 retrieval 從 ~0.79/0.75 拉到 ~0.98(真正的技術貢獻)

## 6. 評估器
* 評估面向及標準:**graph-binding 語意評分(11 維 composite),不只是格式對**
  * 沿 intent 契約路徑把每個 gold metric 綁到輸出子圖,逐維度比對正確性(metric / threshold / statistic / scope / method / window / operator / tenant / topology / contract / precision)
* 關鍵:**精確-IRI 比對** → 吐非官方 namespace 的輸出語意歸零(這就是地板 = 0、且分數差距戲劇化的原因)
* 簡述方法:syntax(Turtle parse)→ vocabulary(unknown pred/type)→ expected-coverage → 11 維 composite

## 7. 四方比較
* [圖一:品質] 四條 composite — **KGE 0.978 ≳ GraphRAG 0.975 ≳ 天花板 0.974**,地板 0.000
* [圖二:token] online token — GraphRAG 2,718 / KGE 2,722 vs 天花板 5,354(**約天花板 51%**),地板 1,532
  * 標明是 **online** token;補一句 prep(建 index / 訓練 KGE)攤提到 @100 後仍低於天花板,避免被質疑沒算前處理成本

## 8. 結論
* **兩條 retrieval ≈ 天花板品質,只用約一半 token** —— retrieval 可取代 prompt-engineering 的詞彙注入
* 限制與未來工作(誠實加分):
  * 收斂是小固定 schema 的性質;metric→method 慣例有邊界(個別題可能貼錯)
  * KGE 偶發 Turtle parse 需單題重跑(可加 parse-retry/repair guard)
  * 未來:scorer 嚴格化、補 KAG-structure 湊真正的第四方、更大 schema 驗證泛化性
