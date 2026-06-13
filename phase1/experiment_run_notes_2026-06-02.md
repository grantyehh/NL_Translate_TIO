# Phase 1 Run Notes - 2026-06-02

**Date**

2026-06-02 Asia/Taipei

**Completed**

本輪完成完整 Phase 1 重新執行與 token usage 評估：

- 重新跑 preprocessing：
  - GraphRAG ontology input rebuild：local TTL processing，token prep cost = 0。
  - KGE training / text embedding artifacts：prep total = 15,501 tokens。
  - KAG KG builder：prep total = 276,204 tokens。
- 重新跑四條 online generation：
  - LLM-only：20/20 cases。
  - GraphRAG：20/20 cases。
  - KGE：20/20 cases。
  - KAG：主流程 19/20，TC007 第一次失敗後已單獨補跑成功，最後 20/20 cases。
- 將 Phase 1 report 分成兩個子目錄：
  - `phase1/output_quality/`
  - `phase1/token_usage/`
- 產生最新品質比較：
  - `phase1/output_quality/compare_four_way.txt`
- 產生最新 token 比較：
  - `phase1/token_usage/compare_token_usage.txt`
- 更新 `progress.md` 的品質表、token 表與 verification 紀錄。

## Output Quality Summary

```text
Experiment     | Cases | Parse OK   | Avg icm  | Avg ontology | Avg metric | Avg JSON nodes | Verbosity OK | Avg node ratio | Intent ID OK
LLM-only       |    20 |     95.00% |   1.0000 |       0.9806 |     1.0000 |          62.75 |      100.00% |         1.0211 |       100.00%
GraphRag       |    20 |    100.00% |   1.0000 |       0.9861 |     1.0000 |          62.75 |      100.00% |         1.0203 |       100.00%
KGE            |    20 |    100.00% |   1.0000 |       0.9944 |     1.0000 |          62.90 |      100.00% |         1.0228 |       100.00%
KAG            |    20 |    100.00% |   0.9900 |       0.9233 |     1.0000 |          61.50 |      100.00% |         0.9978 |       100.00%
```

Interpretation:

- KGE 目前仍是 ontology coverage 最高的方法，avg ontology = 0.9944。
- GraphRAG 與 KGE 都是 20/20 parse OK，ICM / metric coverage 滿分。
- KAG native 也是 20/20 parse OK，但 avg ontology = 0.9233，低於 GraphRAG / KGE。
- LLM-only 這輪格式與 verbosity 明顯比舊紀錄好，但 TC020 仍有 parse / contract 問題，所以 parse OK = 95%。

## Token Usage Summary

```text
Experiment     | Cases | Prep total   | Avg online   | Online total | Avg calls |   Amortized @20 |  Amortized @100 | Amortized @1000
LLM-only       |    20 |            0 |      5201.15 |       104023 |      1.00 |         5201.15 |         5201.15 |         5201.15
GraphRag       |    20 |            0 |     24993.35 |       499867 |      3.00 |        24993.35 |        24993.35 |        24993.35
KGE            |    20 |        15501 |     11526.70 |       230534 |      2.00 |        12301.75 |        11681.71 |        11542.20
KAG            |    20 |       276204 |      5906.35 |       118127 |      1.00 |        19716.55 |         8668.39 |         6182.55
```

Stage-level breakdown:

```text
LLM-only
  online jsonld_generation      104,023

GraphRAG
  online seed_selection           2,902
  online embedding              266,787
  online jsonld_generation      230,178

KGE
  prep text_embedding_artifacts  15,501
  online retrieval_embedding        818
  online jsonld_generation      229,716

KAG
  prep kg_builder               276,204
  online kag_solver             118,127
```

**Learned**

## Why GraphRAG Online Token Is High

GraphRAG online average is high because this implementation keeps most retrieval grounding work in the online path:

- Each case records three online stages: `seed_selection`, `embedding`, and `jsonld_generation`.
- The largest cost is embedding, not seed selection:
  - embedding total = 266,787 tokens across 20 cases.
  - jsonld generation total = 230,178 tokens across 20 cases.
  - seed selection total = 2,902 tokens across 20 cases.
- GraphRAG currently rebuilds / prepares ontology input locally with zero LLM prep token, but at online time it embeds a large term/context surface and then sends a rich RDF traversal context to the generator.
- This design makes quality stable because the generator sees ontology-native context, but it pays that cost per query.

Implication:

- GraphRAG token cost should not be compared only against KAG online average without noting where work is placed.
- GraphRAG could reduce online cost by caching ontology term embeddings / retrieval artifacts in prep, limiting candidate term embedding scope, or more aggressively compressing serialized traversal context.

## Why KAG Online Looks Low Despite Many Steps

KAG online average is low in the current report because the measurement is based on KAG `LLMClient.TokenMeter` rows, not necessarily every API call involved in solver retrieval.

Observed facts:

- KAG prep cost is very high: 276,204 tokens from `kg_builder`.
- KAG online measured cost is 118,127 total tokens, or 5,906.35 tokens/case.
- KAG online `Avg calls = 1.00` is an artifact of how token usage is recorded: one aggregate row per case, not proof that KAG made exactly one model call.
- KAG does much of its expensive knowledge construction before inference: OpenSPG / Neo4j KG construction, chunk processing, and solver artifacts are prepared before test-case generation.
- Many KAG online steps are graph retrieval, table/vector/outline retrieval, parser work, or Docker-backed KG access. These can be slow without directly adding LLM token count.

Important caveat:

- KAG logs showed online `text-embedding-3-small` vectorizer activity and connection errors.
- Current KAG token instrumentation may not capture vectorizer embedding usage if those calls do not flow through the same KAG `LLMClient.TokenMeter`.
- Therefore, current KAG online cost should be described as **measured KAG LLM-meter online tokens**, not complete end-to-end online API token cost.

Implication:

- KAG looks cheap online because prep absorbed a large amount of work and because the current meter may miss some online embedding/vectorizer usage.
- For a fair token comparison, KAG needs call-level instrumentation for vectorizer embedding usage and internal LLM calls, not only aggregate KAG TokenMeter rows.

## KAG Issues Seen During This Run

Runtime / reliability issues:

- Main KAG online run completed 19/20 cases; TC007 failed once with:
  - `list indices must be integers or slices, not str`
- TC007 was later rerun through a small direct runner that preserved the existing token ledger and successfully overwrote `jsonld_outputs/kag/TC007.jsonld`.
- KAG logs repeatedly printed parser warnings:
  - `Exception: Expecting value: line 1 column 1 (char 0)`
  - These appeared around `AtomicQueryRewritePrompt` decoding, but most cases still completed.
- KAG logs repeatedly printed async cleanup warnings:
  - `Task exception was never retrieved`
  - `RuntimeError: Event loop is closed`
  - These appeared non-fatal in this run.
- KAG logs showed embedding connection errors from `text-embedding-3-small`; the pipeline usually continued, but this is a reliability and measurement caveat.

Workflow issues:

- KAG uses a separate venv under `KAG/.venv`; running KAG with the root Python is unsafe.
- KAG Docker stack / KG state matters. If the container or volumes are reset, builder must be rerun.
- `KAG/nl_to_tio.py --resume` skips any existing non-empty output file. Since TC007 had an older output file, `--case TC007 --resume` would have skipped it. The successful retry used a direct runner to preserve the ledger while forcing TC007 regeneration.
- The current `Avg calls` metric is too coarse for KAG because one aggregate row represents a whole solver pass.

Quality issues:

- KAG quality is parse-stable and compact, but ontology coverage is lower than GraphRAG / KGE.
- TC008 had KAG expected element coverage 0.8000.
- KAG TC020 ontology coverage was 0.8000, even though parse and metric coverage passed.
- This suggests native KAG retrieval/generation can satisfy high-level metric structure but sometimes misses specific expected ontology terms or expected elements.

Measurement issues:

- KAG prep token is recorded from the KAG builder TokenMeter.
- KAG online token is recorded from KAG solver TokenMeter.
- KAG embedding/vectorizer token may be undercounted.
- KAG should be reported as `measured` token usage until instrumentation is expanded.

## Method-Level Takeaways

LLM-only:

- Cheapest online method in this run: 5,201.15 tokens/case.
- Quality is surprisingly strong after the current prompt/output contract shape, but parse OK is still 95% due to TC020.
- No prep cost, so amortized cost is identical for N=20 / 100 / 1000.

GraphRAG:

- Highest online token cost: 24,993.35 tokens/case.
- Cost comes from embedding + large ontology-native context sent to generation.
- Quality is strong and stable, but the current design pays retrieval grounding cost per case.

KGE:

- Moderate prep cost and moderate online cost.
- Best ontology coverage in this run.
- Prep amortization is mild: 12,301.75 at N=20, 11,542.20 at N=1000.
- KGE appears to be a good quality/cost middle ground in this specific 20-case setup.

KAG:

- Highest prep cost.
- Lowest measured online cost among knowledge-enhanced methods.
- Most sensitive to environment/container state.
- Needs better token instrumentation before claiming true online cost advantage.
- At small N, amortized cost is high; at large N, prep cost becomes less important.

**Next Steps**

Recommended follow-up work:

1. Improve KAG token instrumentation:
   - capture vectorizer embedding usage;
   - record call-level LLM usage instead of only one aggregate row per case;
   - separate planning / retrieval rewrite / generation stages if KAG exposes those counters.
2. Improve GraphRAG online cost:
   - cache ontology term embeddings in prep;
   - avoid embedding the same large ontology term surface per case;
   - cap or compress traversal context before generation.
3. Improve report wording:
   - label KAG online token as measured KAG LLM-meter usage;
   - label `Avg calls` as recorded usage rows, not physical API calls.
4. Improve KAG reliability:
   - investigate `AtomicQueryRewritePrompt` JSON decode warnings;
   - investigate `Event loop is closed` cleanup errors;
   - add a safe force-rerun single-case path that appends token usage without resetting online ledger.
5. Improve KAG quality:
   - inspect TC008 and TC020 missing expected elements / ontology terms;
   - compare KAG retrieved context with GraphRAG / KGE context for those cases.
