# GraphRag TIO Turtle Workflow

本文件只記錄目前 GraphRag 線的實際流程。主流程為 NL -> TIO Turtle（EVSLA hub-and-spoke：icm:/evsla:/quan: 詞彙）。

## 1. 生成

在 `GraphRag/` 目錄執行：

```bash
python nl_to_tio.py
```

固定輸出到根目錄：

```text
tio_outputs/graphrag/*.ttl
```

`nl_to_tio.py` 預設讀取：

- `../test_cases_20.json`
- `../few_shot_samples.json`
- 既有 GraphRAG index `output/`

## 2. 評分

回到根目錄執行：

```bash
python evaluate_ttl.py graphrag
```

固定輸出：

```text
phase1/phase1_graphrag.json
```

## 3. 比較

通常從根目錄直接跑：

```bash
python run_all_experiments.py --eval-only
```

這會重算四條線的 TIO Turtle 評分與 pairwise comparison。
