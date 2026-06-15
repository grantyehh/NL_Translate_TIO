# KGE Canonical Redesign — Sound Embedding Use over a Shared Output Contract

Date: 2026-06-15

Status: design approved, pending spec review

## 1. Goal

Redesign the KGE retrieval line so it uses knowledge-graph embeddings the way
the literature actually uses them, and so it is a **methodologically legitimate,
fair comparison** against the redesigned GraphRAG line — not a winner-at-all-costs.

> Make KGE canonical: use embeddings only to **retrieve / rank real ontology
> facts** (never to synthesize triples), emit the **same scoped, groundable
> output contract** as GraphRAG, and let the comparison isolate the one variable
> that differs — the term-selection mechanism (embedding-based vs lexical +
> deterministic traversal).

Scope is the KGE line in `TIO_Experiment` (this repo). GraphRAG is reused (its
output-contract modules) but not changed. KAG is out of scope.

## 2. Background — why the current KGE is not canonical (with evidence)

The current KGE structure-only line scored **composite 0.0051 at 8,099 tok/case**
(this round, 40 cases) — near the no-retrieval floor (0.0000) yet 3.4× the
redesigned GraphRAG's cost (0.7867 at 2,369). Inspection of what it actually
feeds the LLM (`kge/retrieve.py`) shows three misuses of otherwise-canonical
ingredients:

1. **TransE entity-cosine "neighbor expansion"** (`get_kge_ranked_entities`):
   TransE entity vectors are trained for the translational objective
   (h + r ≈ t), **not** for entity-to-entity cosine similarity. Cosine-nearest
   entities are therefore not "related" — this pulls in irrelevant terms
   (`mf:c` a vertical-offset parameter, `fun:arityMin`, `imo:IntentRejected`, …).
2. **"Predicted likely triples" dumped as facts** (`predict_likely_triples` +
   `format_grounded_kge_context`): TransE link-prediction output is injected
   into the prompt labelled "likely triples", including unverified, low-score,
   nonsensical predictions, e.g. `log:matchOne rdf:type evsla:fiveMinuteWindow`,
   `ig:GuaranteeStateCompliant rdfs:subClassOf evsla:hasSpoke`. Canonically,
   link-prediction is for KG completion (rank candidates, then verify) or to
   decide which **real** triple to retrieve — never to hand synthetic triples to
   a generator. TransE is also known-unreliable for 1-to-N / N-to-N relations.
3. **Encyclopedic term-hint dump**: top-k terms are emitted each with their full
   `rdfs:comment` paragraph, no relevance filtering, no `@prefix` block, mixing
   CURIEs and full URIs — producing the 8k-token noise.

The TransE model is also trained on the ontology's URI-to-URI triples, which in
a schema are predominantly TBox (`subClassOf` / `type` / `domain` / `range`) over
classes/properties (not instances). It is therefore data-starved and learns
taxonomy noise, compounding misuses 1 and 2.

## 3. Method Positioning

KGE remains a **knowledge-graph-embedding retrieval** line. Both embeddings are
used in their sound roles:

- **Text embeddings** → dense entity retrieval (entry grounding). This also
  captures vocabulary variation that lexical matching misses (e.g. Chinese
  "延遲" → `evsla:latency`, "丟包" → `evsla:packetLoss`).
- **TransE (KG) embeddings** → link-prediction in its canonical form: **rank
  real triples** (existing `(h, r, t)` in the graph) by plausibility
  `-‖h + r − t‖`, to expand from seed entities to related **real** entities.
  Never synthesize triples; never present non-existent edges.

The selection feeds the **same output contract** as GraphRAG, so the lines
differ only in how seeds/terms are chosen.

## 4. Architecture and Data Flow

```text
NL intent
  -> [reuse trained artifacts]
       entity_ids, entity_text_embeddings (N×1536), entity_kge_embeddings (N×128),
       relation_ids, relation_kge_embeddings (R×128), real triples (triples.tsv)
  -> entry grounding: cosine(query_text_emb, entity_text_embeddings) -> top-k seed entity URIs
  -> TransE expansion: rank REAL triples containing a seed by -‖h+r−t‖; keep top-k;
       add their entities to the grounded set  (real triples only — never synthesized)
  -> SHARED output-contract derivation (GraphRag modules):
       grounded set -> traverse_connective -> reached roles + connective relations
                    -> closed_vocab_for_reached_roles -> closed vocab per reached role
  -> SHARED serialization: context_builder.serialize_context
       (@prefix + grounded terms + connective relations + closed vocab)
  -> inject into structure_only prompt -> LLM generates TIO Turtle
```

Per-case online cost = 1 query-embedding call + 1 generation call (TransE
expansion is local matrix math; no extra LLM call).

## 5. Reused Artifacts (already trained; `train.py` unchanged)

`kge/train.py` and its outputs in `KGE/KGE-based-graphrag/kge_data/` are kept
as-is: `entity_ids.json`, `entity_text_embeddings.npy`,
`entity_kge_embeddings.npy`, `relation_ids.json`, `relation_kge_embeddings.npy`,
`triples.tsv`, `manifest.json` (text embedding model). The redesign changes only
how these artifacts are *used* at query time.

## 6. Shared Output-Contract Modules (coupling decision)

KGE reuses, by importing from `GraphRag/` (adding it to `sys.path`, per the
repo's existing convention), without duplication:

- `resource_index.py` — `build_resource_index`, `OntologyResource` (`role_class`).
- `graph_relations.py` — `traverse_connective`, `closed_vocab_for_reached_roles`.
- `context_builder.py` — `serialize_context`, `PREFIXES`.

This introduces a KGE → GraphRag dependency. Chosen over extracting a shared
`tio_retrieval/` package on YAGNI grounds (only two lines share it today). If a
third consumer appears, extract then.

## 7. KGE Code Changes

### 7.1 New: `KGE/KGE-based-graphrag/kge/select.py`

Clean Approach-A selection. Functions:

- `text_ground(query, *, top_k) -> list[str]` — embed the query (existing
  `_embed_query`), cosine vs `entity_text_embeddings`, return top-k entity URIs.
- `transe_expand(seed_uris, *, top_k) -> list[str]` — load real `triples.tsv`;
  for triples containing a seed as head or tail, score by `-‖h+r−t‖` using the
  TransE entity/relation matrices; return the entities of the top-k **real**
  triples. Returns only entities that appear in real triples; never fabricates.
- `build_kge_context(query, *, case_id=None) -> str` — orchestrate
  `text_ground` + `transe_expand` → grounded URI set → GraphRag
  `traverse_connective` / `closed_vocab_for_reached_roles` →
  `context_builder.serialize_context`. Returns the context string (same shape as
  GraphRAG's).

Hyperparameters (entry `top_k`, expansion `top_k`) are module constants, tuned
small to keep the context scoped.

### 7.2 Modify: `kge/retrieve.py`

- **Remove**: the KGE-cosine "neighbor expansion" branch of
  `get_kge_ranked_entities`; `predict_likely_triples`;
  `format_grounded_kge_context`; the dump body of `format_kge_context_for_prompt`.
- **Keep**: artifact loaders (`_load_arrays`, `_load_kge_link_arrays`,
  `_load_triple_rows`), `kge_ready` / `kge_link_prediction_ready`, the
  `_embed_query` helper and its token accounting, `trans_e_score`, `_uri_to_curie`.
  `select.py` reuses these loaders/helpers.

### 7.3 Modify: `KGE/KGE-based-graphrag/nl_to_tio.py`

Replace the per-case retrieval call `format_kge_context_for_prompt(nl_intent,
case_id=...)` with `select.build_kge_context(nl_intent, case_id=...)`. No other
change: it already supports `--prompt-profile structure_only` and writes to the
`kge_structure` experiment key.

## 8. Evaluation and Success Criteria

Re-run `kge_structure` over the 40 cases, then
`evaluate_ttl.py kge_structure --test-cases test_cases_40.json`. Compare against
this round's existing numbers:

```text
                       | Composite | Tok/case  | source
KGE-structure (old)    |  0.0051   |  8,099    | current misused pipeline
KGE-structure (canon)  |   ???     |   ???     | this redesign
GraphRAG-structure     |  0.7867   |  2,369    | mechanism comparator
LLM-only-structure     |  0.0000   |  1,432    | floor
```

Success:

1. composite **clearly leaves ~0** (proves canonical selection grounds to
   official vocabulary), and
2. tok/case **far below 8,099** (synthetic-triple dump + encyclopedic hints
   removed), and
3. output is **clean**: contains the `@prefix` block, only reached-role closed
   vocab, no `TransE score=` / "Predicted likely triples" text, no
   `subClassOf` / `domain` / `range` plumbing lines, no fabricated triples.

Matching GraphRAG-structure is **not** a hard requirement — a clean,
methodologically-sound mechanism comparison is itself the deliverable (see §11).

## 9. Testing

Offline gate (no API tokens):

- `transe_expand` returns only triples present in `triples.tsv` (never
  fabricated); given a seed, top results are real `(h, r, t)` rows.
- `build_kge_context` output: includes the `@prefix` block; closed-vocab section
  lists only reached roles; contains **no** `TransE score=`, **no** "Predicted
  likely triples", **no** `subClassOf` / `domain` / `range` fact lines; token
  count within the configured budget.
- removal regression: `kge/retrieve.py` no longer exports
  `predict_likely_triples` / `format_grounded_kge_context`, and
  `get_kge_ranked_entities` no longer performs KGE-cosine neighbor expansion.

Online smoke (1 case, needs API key):

- `text_ground` grounds a non-lexical query term (Chinese "延遲") to
  `evsla:latency` via the text embedding.
- one `kge_structure` case generates; context length is far below the old dump.

Do not spend API tokens before the offline gate passes.

## 10. Scope and Non-Goals

- GraphRAG is **not** modified; its three output-contract modules are imported.
- `kge/train.py` and the trained artifacts are **not** changed.
- No new evaluator; reuse `semantic_eval.py` via `evaluate_ttl.py`.
- No synthetic triples are ever presented to the LLM (the core correction).
- No shared-package extraction (YAGNI; KGE imports from `GraphRag/`).
- KAG, and any change to the strong/weak baselines, are out of scope.

## 11. Captured Nuances

- **Small-schema tension is expected and acceptable.** On a tiny fixed schema
  the SLA role structure is a schema fact (domain/range), so once a text-grounded
  value entity activates the SlaExpectation hub (via the shared
  `traverse_connective`), the reached roles are largely determined by the schema,
  not by TransE. The TransE expansion may therefore add little. That is an
  **honest, fair finding** — the experiment is allowed to conclude "the KG
  embedding adds little beyond text grounding on this task," which is far more
  informative than the current garbage 0.0051.
- **TransE expansion is constrained to real triples**, so even if it is weak it
  cannot inject the nonsense the old predicted-triples dump did; the worst case
  is a few extra real (and possibly irrelevant) schema entities, which the
  shared role-scoping then filters by `role_class`.
- The KGE → GraphRag import coupling is deliberate and documented; revisit only
  if a third consumer needs the contract.
