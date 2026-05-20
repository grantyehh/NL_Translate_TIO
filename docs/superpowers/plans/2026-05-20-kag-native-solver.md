# KAG Native Solver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route KAG outputs through the native KAG builder/solver/generator flow so final TIO JSON-LD is produced by the KAG solver generator stage.

**Architecture:** Keep `KAG/example_project` as the OpenSPG/KAG project. Add a TIO-specific KAG generator and prompt under `KAG/example_project/solver/`, configure `kag_solver_pipeline_tc` to use it, and simplify `KAG/nl_to_tio.py` so it calls `pipeline.ainvoke(...)` and writes the returned JSON-LD.

**Tech Stack:** Python, OpenSPG KAG registry, KAG `SolverPipelineABC`, KAG `GeneratorABC`, unittest.

---

### Task 1: TIO KAG Generator

**Files:**
- Create: `KAG/example_project/solver/tio_jsonld_generator.py`
- Test: `KAG/test_tio_jsonld_generator.py`

- [ ] Write failing tests for context formatting, prompt parsing, and generator LLM invocation.
- [ ] Implement a registered `tio_jsonld_generator`.
- [ ] Implement a registered `tio_jsonld_generator_prompt`.
- [ ] Run `python -m unittest KAG/test_tio_jsonld_generator.py -v`.

### Task 2: KAG Pipeline Wiring

**Files:**
- Modify: `KAG/example_project/kag_config.template.yaml`
- Modify: `KAG/example_project/kag_config.yaml`
- Modify: `KAG/nl_to_tio.py`
- Test: `KAG/test_nl_to_tio.py`

- [ ] Write failing tests proving `nl_to_tio.py` calls KAG solver answer generation rather than returning retrieved chunks.
- [ ] Wire `kag_solver_pipeline_tc.generator.type` to `tio_jsonld_generator`.
- [ ] Replace external OpenAI JSON-LD generation in `nl_to_tio.py` with KAG solver invocation.
- [ ] Run `python -m unittest KAG/test_nl_to_tio.py -v`.

### Task 3: Verification

**Files:**
- Modify: `KAG/example_project/README.md`

- [ ] Update README to document native KAG solver generation.
- [ ] Run focused KAG unit tests.
- [ ] Run relevant root tests that cover experiment wiring/evaluation.
