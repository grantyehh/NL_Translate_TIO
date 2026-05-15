# KAG (openspg-kag 0.8.0) Patches

> **背景**:`TIO_Experiment/KAG/openspg-kag/` 是 `git clone --depth 1 https://github.com/OpenSPG/KAG.git` 拉下來的 upstream 副本,被 .gitignore 排除。
>
> 為了讓 KAG 對接 **OpenAI 官方 API + 中文 prompt 路徑** 順利工作,本檔記錄所有對 upstream source 的修改。
> **每次 re-clone 後須重新 apply**(或寫成 patch file 自動化)。

---

## ✅ 已套用的 patch(0.8.0,2026-05-14~15)

### Patch 1:`chat_template_kwargs` 對 OpenAI 端點條件式發送

**檔案**:`kag/common/llm/openai_client.py` 約 line 78

**問題**:KAG 預設每次 LLM call 都送 `extra_body={"chat_template_kwargs": {"enable_thinking": ...}}`。這是 vLLM / Ollama / Qwen 等模型的「think mode」開關,**OpenAI 官方 API 不認此參數**,直接 400 reject。

**改動**:

```python
# 原本:
self.extra_body = {"chat_template_kwargs": {"enable_thinking": self.think}}

# 改成:
# PATCH (TIO_Experiment 2026-05-14): chat_template_kwargs is a vLLM/Ollama/Qwen-compat
# param that OpenAI's official API rejects ("Unknown parameter"). Only emit it when
# the user opted into think mode OR when not pointing at api.openai.com.
if self.think or "api.openai.com" not in (base_url or ""):
    self.extra_body = {"chat_template_kwargs": {"enable_thinking": self.think}}
else:
    self.extra_body = {}
```

**影響**:OpenAI 端點正常;對 vLLM/Ollama/Qwen 等行為不變。

---

### Patch 2:`max_tokens` → `max_completion_tokens` 對新版 OpenAI model

**檔案**:`kag/common/llm/openai_client.py` 4 處 call site(line 138, 226, 382, 436)

**問題**:OpenAI 從 GPT-4o / o1 系列開始要求用 `max_completion_tokens`,新版 model(gpt-5.x 等)若用舊 `max_tokens` keyword 會 400 reject:

```
"Unsupported parameter: 'max_tokens' is not supported with this model.
 Use 'max_completion_tokens' instead."
```

**改動**:4 個 call site 統一改條件式 keyword:

```python
# 原本(兩種 pattern):
max_tokens=self.max_tokens if self.max_tokens > 0 else NOT_GIVEN,
max_tokens=self.max_tokens,

# 改成:
**{("max_completion_tokens" if "api.openai.com" in (self.base_url or "") else "max_tokens"): (self.max_tokens if self.max_tokens > 0 else NOT_GIVEN)},
**{("max_completion_tokens" if "api.openai.com" in (self.base_url or "") else "max_tokens"): self.max_tokens},
```

**影響**:對 OpenAI 新 model 正常;對 OpenAI 舊 model / vLLM / Ollama 行為不變(`max_tokens` 仍適用)。

---

## ⏳ 推薦套用但**尚未套用**的 patch

> 這 2 個觀察自 nl_to_tio.py 第一輪全量 run(2026-05-15 01:00 起跑)。
> 因 run 已跑到 TC007,中斷重來 cost 高於等完,所以**留給下次 re-run 或別人 reproduce 時套用**。
> 套用後預估**省 30-60% 執行時間**(無 planner retry)。

### Patch 3:中文 prompt template 加 string-ID 範例

**檔案**:`kag/solver/prompt/retriever_static_planning_prompt.py`

**問題**:`template_zh.example.output` **沒有任何含 `dependent_task_ids` 內容的範例**(全部空 list `[]`),導致 LLM 不知道該用 string 還 int。
`template_en` 版本則有明確示範(`"dependent_task_ids": ["0"]`)。

我們 `kag_config.yaml` 是 `language: zh`,所以踩到雷:**~50% 的 query LLM 隨機吐 `[0, 1]`(int)而不是 `["0", "1"]`(string),觸發 Patch 4 那邊的 KeyError 後 retry。**

**建議改動**(template_zh.example.output,line 46-57):

```python
"output": {
    "0": {
        "executor": "Retriever",
        "dependent_task_ids": [],
        "arguments": {"query": "张学友出演过的电影列表"},
    },
    "1": {
        "executor": "Retriever",
        "dependent_task_ids": [],
        "arguments": {"query": "刘德华出演过的电影列表"},
    },
    # 新增第 3 個 task 示範 string IDs:
    "2": {
        "executor": "Retriever",
        "dependent_task_ids": ["0", "1"],   # ← string,不是 int
        "arguments": {"query": "对比电影列表,找出张学友和刘德华共同出演的电影"},
    },
},
```

**強度**:⭐⭐ — LLM 大多時候會學會,但偶爾仍會回 int。

---

### Patch 4:`parse_response` 容忍 int / string dependent_task_ids

**檔案**:`kag/interface/solver/planner_abc.py` 約 line 191

**問題**:KAG 期望 `dependent_task_ids` 內每個 id 都是 string(對應 task_map 的 string key);但 LLM 經常吐 int → 觸發 `KeyError: 0`(int 0 不是 string "0",lookup miss)。

```python
# 觀察到的 traceback:
File ".../kag/interface/solver/planner_abc.py", line 191, in create_tasks_from_dag
    task_map[task_order].add_parent(task_map[dep])
                                    ~~~~~~~~^^^^^
KeyError: 0
```

**建議改動**(1 行):

```python
# 原本:
task_map[task_order].add_parent(task_map[dep])

# 改成:
task_map[task_order].add_parent(task_map[str(dep)])   # tolerate int / string dep IDs
```

**強度**:⭐⭐⭐ — 100% 修(LLM 怎麼吐都 work)。是最防禦性的修法,建議**永久 apply**。

---

## 套 patch 後驗證

```bash
cd /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/KAG
source .venv/bin/activate
set -a && source /Users/grantyeh/Grant/Project/CHT/.env && set +a
cd example_project
./render_config.sh                                # 渲染 config
knext project restore --host_addr http://127.0.0.1:8887 --proj_path .  # 註冊專案
knext schema commit                                # 推 schema
python builder/indexer.py                          # 灌 KG(checkpoint 會跳過已灌)
cd ..
python nl_to_tio.py --case TC001 --verbose         # 試水單題
python nl_to_tio.py                                # 全 20 題
```

預期:**Patch 3 + 4 套上後,KeyError: 0 應該降到 0 次**,20 題完成時間從 ~15 分鐘 →  ~10 分鐘。

---

## 觀察到但未深究的非致命 issue

### `Event loop is closed` RuntimeError(每題 query 結束時)

**現象**:`nl_to_tio.py` 用 `asyncio.run(_kag_retrieve_async(...))` 對每題 query,每次 run 後 loop 被關掉。
KAG 內部 httpx connection pool / OpenAI async client 試圖在 loop 關閉後做 cleanup → `RuntimeError: Event loop is closed`。

**影響**:**非致命**。retrieved_chunks 在 exception 出現前已填好,我們的 try/except 接住後繼續。但每題 stderr 噴一堆 stack trace,log noisy。

**修法**(未做):把 `nl_to_tio.py` 改成單一 event loop 跑所有 query:

```python
async def main_async():
    for tc in test_cases:
        context = await _kag_retrieve_async(...)
        ...

asyncio.run(main_async())
```

工時 ~30 分鐘,影響面僅本檔。

---

### atomic_query extractor `'list' object has no attribute 'split'`

**現象**:builder 階段偶爾出現:
```
File ".../kag/builder/prompt/atomic_query_extract_prompt.py", line 57, in parse_response
    questions = response.split("\n")
AttributeError: 'list' object has no attribute 'split'
```

**原因**:gpt-5.4 對某些 chunk 回了 structured list 而非 newline-joined string。`atomic_query_extract_prompt.parse_response` 假設 string。

**影響**:**非致命**。KAG 重試 N 次後跳過該 chunk,其他 extractor 仍正常產出。觀察:16 個 md 全量灌料 0 failures(checkpoint 有跳過部分)。

**修法**(未做):`parse_response` 加 fallback:
```python
if isinstance(response, list):
    response = "\n".join(str(x) for x in response)
questions = response.split("\n")
```
