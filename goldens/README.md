# Golden Answers

這個資料夾放的是 `phase-2 evaluator` 用的人工標準答案。

設計原則：

- 不要求生成結果和參考 Turtle 逐字相同。
- 先比對關鍵元素、關鍵 triple pattern、關鍵值。
- `golden_ttl_file` 是人工審核過的參考表示，不代表唯一合法答案。

目前檔案：

- `golden_cases.json`: 5 題高價值 metadata
- `golden_cases.sample.json`: 2 題最小示範 metadata
- `TC002.ttl`, `TC004.ttl`, `TC005.ttl`, `TC014.ttl`, `TC020.ttl`: 參考 Turtle

欄位說明：

- `golden_ttl_file`: 參考 Turtle 檔案位置
- `must_have_elements`: 至少要出現的核心 TIO 元素
- `must_have_triples`: 必須出現的 triple pattern。`?var` 表示變數，不要求固定 URI
- `expected_values`: 應該被正確表達的值、單位、比較方向
- `must_not_have_predicates`: 明確不希望出現的 hallucinated predicate
- `notes`: 對 evaluator 或人工審查的補充說明
