# Weak-prompt Recipe CP Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `--weak-prompt` mode (weak system prompt + no few-shot + `_weak` outputs) to all four lines, plus a CP comparator, so we can run Arm 1 (LLM-only strong) vs the floor and the three independent Arm-2 retrieval recipes and compare quality (semantic) against token cost.

**Architecture:** A `weak_prompt` flag in the shared prompt builder strips all domain knowledge; each `nl_to_tio.py` gets `--weak-prompt` (which also forces no few-shot and routes to `_weak` paths/tags); the evaluator gains `_weak` keys; a new comparator prints the 5-condition CP table.

**Tech Stack:** Python 3.13, rdflib, OpenAI SDK, unittest. **Spec:** `docs/superpowers/specs/2026-06-13-weak-prompt-retrieval-substitution-design.md`

---

## File Structure

- `evsla_prompt.py` — `weak_prompt` branch (drop all domain blocks).
- `LLM-only/`, `GraphRag/`, `KGE/KGE-based-graphrag/` `nl_to_tio.py` — `--weak-prompt` via a module `WEAK` flag.
- `evaluate_ttl.py` — 4 `_weak` experiment keys.
- `KAG/example_project/solver/tio_turtle_generator.py` — `tio_turtle_generator_prompt_weak`.
- `KAG/example_project/kag_config.template.yaml` — templated `generated_prompt.type`.
- `KAG/nl_to_tio.py` — `--weak-prompt` (no few-shot + `_weak` output + `kag_weak` token tag).
- `compare_recipe_cp.py` (new) — 5-condition semantic + token CP table.

---

### Task 1: `weak_prompt` branch in evsla_prompt.py

**Files:** Modify `evsla_prompt.py`; Test `test_evsla_prompt.py` (new).

- [ ] **Step 1: Failing test** — create `test_evsla_prompt.py`:
```python
import unittest
from evsla_prompt import build_evsla_system_prompt

class TestWeak(unittest.TestCase):
    def test_weak_drops_domain_knowledge(self):
        w = build_evsla_system_prompt("TC001", retrieval_mode="GraphRAG", weak_prompt=True)
        for banned in ["evsla:latency", "evsla:hasMetric", "quan:smaller", "Metric mappings",
                       "Graph structure", "hubToAllSpokes", "p95"]:
            self.assertNotIn(banned, w)
        self.assertIn("Turtle", w)                 # format kept
        self.assertIn("tc001", w)                  # ex: namespace kept
        self.assertIn("GraphRAG", w)               # retrieval note kept

    def test_strong_unchanged(self):
        s = build_evsla_system_prompt("TC001")
        self.assertIn("evsla:hasMetric", s)
        self.assertIn("quan:smaller", s)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run, expect FAIL** — `python3 -m unittest test_evsla_prompt -v` (weak_prompt arg not accepted / domain terms present).

- [ ] **Step 3: Implement** — in `evsla_prompt.py`, change the signature to
`def build_evsla_system_prompt(tc_id: str, retrieval_mode: str | None = None, weak_prompt: bool = False) -> str:`
and, immediately after `retrieval_note` is computed, add:
```python
    if weak_prompt:
        return f"""You generate TIO Turtle (RDF) for Enterprise VPN hub-and-spoke SLA intents only.
Output ONLY valid, parseable Turtle. Never output JSON, JSON-LD, Markdown, prose, 5G slices, datacenter fabric, or generic service delivery.

Declare every @prefix you use so the Turtle parses. Use ex: <http://example.org/tio-instance/{tc_id.lower()}/> for instances.
{retrieval_note}Core semantics must be carried by triples, not only by rdfs:comment.
"""
```

- [ ] **Step 4: Run, expect PASS** — `python3 -m unittest test_evsla_prompt -v`.

- [ ] **Step 5: Commit** — `git add evsla_prompt.py test_evsla_prompt.py && git commit -m "feat(prompt): weak_prompt variant drops all domain knowledge"`

---

### Task 2: `--weak-prompt` in the three main lines

**Files:** Modify `LLM-only/nl_to_tio.py`, `GraphRag/nl_to_tio.py`, `KGE/KGE-based-graphrag/nl_to_tio.py`.

Apply the **same five edits** to each file (the only per-file differences are the line
name `llm_only`/`graphrag`/`kge`, the `retrieval_mode`, and KGE's output base
`root.parent.parent` vs `root.parent`):

- [ ] **Step 1: Add a module flag.** After the `CHAT_MODEL = ...` line add:
```python
WEAK = False  # set True by --weak-prompt: weak system prompt + no few-shot + _weak outputs
```

- [ ] **Step 2: Suffix the output dir.** In `output_path_for_case`, change the `"llm_only"`
(resp. `"graphrag"`, `"kge"`) segment to `("llm_only" + ("_weak" if WEAK else ""))`.

- [ ] **Step 3: Suffix the token path.** In `token_usage_path`, change the filename to
`f"token_usage_llm_only{'_weak' if WEAK else ''}.json"` (resp. graphrag/kge).

- [ ] **Step 4: Thread weak into the prompt + token tag.**
  - `build_system_prompt`: pass `weak_prompt=WEAK` (LLM-only: `build_evsla_system_prompt(tc_id, weak_prompt=WEAK)`; GraphRag: `..., retrieval_mode="GraphRAG", weak_prompt=WEAK`; KGE: `..., retrieval_mode="KGE", weak_prompt=WEAK`).
  - In the `record_usage(...)` call, change `experiment="llm_only"` to `experiment="llm_only" + ("_weak" if WEAK else "")` (resp. graphrag/kge).

- [ ] **Step 5: Add the CLI flag + force no-few-shot.** In `main()`, add after the other `add_argument`s:
```python
    parser.add_argument("--weak-prompt", action="store_true",
                        help="Weak system prompt + no few-shot + _weak outputs")
```
and right after `args = parser.parse_args()`:
```python
    global WEAK
    WEAK = args.weak_prompt
    if args.weak_prompt:
        args.no_few_shot = True
```

- [ ] **Step 6: Verify routing without spending tokens** — for each line:
```bash
python3 -c "
import importlib.util, sys
sys.argv=['x','--weak-prompt']
spec=importlib.util.spec_from_file_location('m','LLM-only/nl_to_tio.py')
" 2>/dev/null || true
cd LLM-only && python3 - <<'PY'
import nl_to_tio as m
m.WEAK=True
print(m.output_path_for_case(m.Path('.').resolve(), 'TC001').as_posix().split('tio_outputs/')[-1])
print(m.token_usage_path(m.Path('.').resolve()).name)
PY
cd ..
```
Expected: `llm_only_weak/TC001.ttl` and `token_usage_llm_only_weak.json`.

- [ ] **Step 7: Commit** — `git add LLM-only/nl_to_tio.py GraphRag/nl_to_tio.py KGE/KGE-based-graphrag/nl_to_tio.py && git commit -m "feat: --weak-prompt (weak prompt + no few-shot + _weak outputs) for the three main lines"`

---

### Task 3: `_weak` experiment keys in evaluate_ttl.py

**Files:** Modify `evaluate_ttl.py`.

- [ ] **Step 1: Add four keys to the `EXPERIMENTS` dict** (after the existing `kag` entry):
```python
    "llm_only_weak": {"label": "LLM-only-weak", "outputs_dir": ROOT / "tio_outputs" / "llm_only_weak",
                      "report": ROOT / "phase1" / "phase1_llm_only_weak.json"},
    "graphrag_weak": {"label": "GraphRAG-weak", "outputs_dir": ROOT / "tio_outputs" / "graphrag_weak",
                      "report": ROOT / "phase1" / "phase1_graphrag_weak.json"},
    "kge_weak": {"label": "KGE-weak", "outputs_dir": ROOT / "tio_outputs" / "kge_weak",
                 "report": ROOT / "phase1" / "phase1_kge_weak.json"},
    "kag_weak": {"label": "KAG-weak", "outputs_dir": ROOT / "tio_outputs" / "kag_weak",
                 "report": ROOT / "phase1" / "phase1_kag_weak.json"},
```

- [ ] **Step 2: Verify the keys resolve** — `python3 -c "from evaluate_ttl import EXPERIMENTS; print([k for k in EXPERIMENTS if k.endswith('_weak')])"`
Expected: `['llm_only_weak', 'graphrag_weak', 'kge_weak', 'kag_weak']`.

- [ ] **Step 3: Commit** — `git add evaluate_ttl.py && git commit -m "feat(eval): add _weak experiment keys"`

---

### Task 4: KAG weak prompt + flag

**Files:** Modify `KAG/example_project/solver/tio_turtle_generator.py`, `KAG/example_project/kag_config.template.yaml`, `KAG/nl_to_tio.py`.

- [ ] **Step 1: Register a weak prompt class.** In `tio_turtle_generator.py`, after the
`TIOTurtleGeneratorPrompt` class, add a sibling registered under a new name whose
`template_en` keeps only format + prefix-declaration + `$query/$content/$tc_id/$few_shot_block`
placeholders and drops the EVSLA structure / metric mappings / comparison-direction:
```python
@PromptABC.register("tio_turtle_generator_prompt_weak")
class TIOTurtleGeneratorPromptWeak(TIOTurtleGeneratorPrompt):
    template_en = """You are the final generator inside a KAG solver pipeline for the TIO Experiment.
You generate TIO Turtle (RDF) for Enterprise VPN hub-and-spoke SLA intents only.
Use the KAG solver context below as grounded evidence. Output ONLY valid, parseable Turtle.
Never output JSON, JSON-LD, Markdown, prose, 5G slices, datacenter fabric, or generic service delivery.
Declare every @prefix you use so the Turtle parses. Use ex: with the current test case ID for instances.
Core semantics must be carried by triples, not only by rdfs:comment.

Current test case ID: $tc_id

Natural language intent:
$query

KAG solver context:
$content
"""
    template_zh = template_en
```

- [ ] **Step 2: Templatize the config.** In `kag_config.template.yaml`, change
`type: tio_turtle_generator_prompt` (under `generator.generated_prompt`) to
`type: {{ TIO_GENERATOR_PROMPT | default("tio_turtle_generator_prompt") }}`.

- [ ] **Step 3: KAG `--weak-prompt` flag.** In `KAG/nl_to_tio.py`:
  - add a module flag `WEAK = False` near the top;
  - in `output_path_for_case`, change `"kag"` to `("kag" + ("_weak" if WEAK else ""))`;
  - in the `record_usage_counts(...)` call change `experiment="kag"` to `experiment="kag" + ("_weak" if WEAK else "")`;
  - in `main()` add `parser.add_argument("--weak-prompt", action="store_true")`, and after parse:
    `global WEAK; WEAK = args.weak_prompt` and `if args.weak_prompt: args.no_few_shot = True`.

- [ ] **Step 4: Verify the weak prompt class imports** —
`KAG/.venv/bin/python -c "import sys; sys.path.insert(0,'KAG/example_project/solver'); import ast; ast.parse(open('KAG/example_project/solver/tio_turtle_generator.py').read()); print('ok')"`
Expected: `ok`.

- [ ] **Step 5: Commit** — `git add KAG/example_project/solver/tio_turtle_generator.py KAG/example_project/kag_config.template.yaml KAG/nl_to_tio.py && git commit -m "feat(kag): weak generator prompt + --weak-prompt"`

---

### Task 5: CP comparator

**Files:** Create `compare_recipe_cp.py`.

- [ ] **Step 1: Write the comparator:**
```python
#!/usr/bin/env python3
"""Recipe CP table: semantic quality vs token cost over the 5 conditions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P1 = ROOT / "phase1"
CONDITIONS = [
    ("LLM-only-strong", "llm_only"),
    ("LLM-only-weak",   "llm_only_weak"),
    ("GraphRag-weak",   "graphrag_weak"),
    ("KGE-weak",        "kge_weak"),
    ("KAG-weak",        "kag_weak"),
]
DIMS = ["metric","threshold","statistic","scope","measurement_method","time_window",
        "operator","tenant","topology","contract","precision"]

def load(p):
    return json.load(open(p)) if p.is_file() else None

def main():
    rows = []
    for name, key in CONDITIONS:
        q = load(P1 / f"phase1_{key}.json")
        t = load(P1 / "token_usage" / f"token_usage_{key}.json")
        if not q:
            rows.append((name, None)); continue
        sem = [x["semantic"] for x in q if x.get("semantic")]
        n = len(sem) or 1
        comp = sum(s["composite"] for s in sem) / n
        dims = {d: sum(s["dimensions"].get(d, 0.0) for s in sem) / n for d in DIMS}
        parse_ok = sum(1 for x in q if x.get("parse_ok")) / len(q)
        tok = sum(int(e.get("total_tokens", 0) or 0) for e in t) if t else 0
        rows.append((name, dict(comp=comp, dims=dims, parse=parse_ok, tok=tok, cases=len(q))))
    print("Recipe CP — semantic quality vs token cost")
    print("=" * 92)
    hdr = f"{'Condition':16} | {'Parse':6} | {'Composite':9} | {'TotalTok':10} | {'Tok/case':9} | {'CP(comp/ktok)':13}"
    print(hdr); print("-" * len(hdr))
    for name, r in rows:
        if r is None:
            print(f"{name:16} | (no data)"); continue
        per = r["tok"] // r["cases"] if r["cases"] else 0
        cp = (r["comp"] / (per / 1000)) if per else 0.0
        print(f"{name:16} | {r['parse']*100:5.0f}% | {r['comp']:9.4f} | {r['tok']:10,} | {per:9,} | {cp:13.3f}")
    print()
    print("Per-dimension (semantic):")
    dh = f"{'Condition':16} | " + " | ".join(f"{d[:5]:>5}" for d in DIMS)
    print(dh); print("-" * len(dh))
    for name, r in rows:
        if r is None: continue
        print(f"{name:16} | " + " | ".join(f"{r['dims'][d]:5.2f}" for d in DIMS))

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke (strong only present yet)** — `python3 compare_recipe_cp.py`
Expected: LLM-only-strong row populated; weak rows show "(no data)" until Task 6 runs.

- [ ] **Step 3: Commit** — `git add compare_recipe_cp.py && git commit -m "feat(eval): recipe CP comparator (semantic vs token, 5 conditions)"`

---

### Task 6: Run the weak experiment + record

**Files:** none (run only). Requires `.env` key; Docker stack up for KAG.

- [ ] **Step 1: Floor + two main weak lines** (system python3):
```bash
set -a && source .env && set +a
( cd LLM-only && python3 nl_to_tio.py --weak-prompt )
( cd GraphRag && python3 nl_to_tio.py --weak-prompt )
( cd KGE/KGE-based-graphrag && python3 nl_to_tio.py --weak-prompt )
```
(LLM-only `--weak-prompt` = the floor: weak prompt, no few-shot, no retrieval.)

- [ ] **Step 2: KAG weak**:
```bash
set -a && source .env && set +a
export GRAPHRAG_LLM_MODEL=gpt-5.4 GRAPHRAG_EMBEDDING_MODEL=text-embedding-3-small TIO_GENERATOR_PROMPT=tio_turtle_generator_prompt_weak
( cd KAG/example_project && bash render_config.sh )
( cd KAG && /Users/grantyeh/Grant/Project/CHT/TIO_Experiment/KAG/.venv/bin/python nl_to_tio.py --weak-prompt )
```

- [ ] **Step 3: Evaluate the four weak conditions:**
```bash
for k in llm_only_weak graphrag_weak kge_weak kag_weak; do python3 evaluate_ttl.py "$k"; done
```

- [ ] **Step 4: CP table:** `python3 compare_recipe_cp.py`

- [ ] **Step 5: Record the CP result in `progress.md`** (new section: experiment architecture 2 — weak recipe CP).

---

## Self-Review notes

- **Spec coverage:** weak prompt §3 → Task 1; few-shot removal §4 → Task 2/4 (`--weak-prompt` forces `no_few_shot`); output isolation §5 → Task 2/4 `_weak` paths+tags; evaluator §6 → Task 3 keys + reuse semantic block; CP comparator §6 → Task 5; conditions §2 (5 independent) → Task 6 runs each separately; floor = LLM-only `--weak-prompt`.
- **Placeholder scan:** none.
- **Type consistency:** module flag named `WEAK` in all four `nl_to_tio.py`; `_weak` suffix consistent across output dir / token file / experiment tag / evaluate_ttl keys / comparator keys.
