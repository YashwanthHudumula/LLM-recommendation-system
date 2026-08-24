# Project history and architecture evolution

## 1. Research objective

The project asks whether personality-conditioned recommendation prompts alter who or what gets
exposure in an LLM recommender. It combines:

- user-side change relative to a paired neutral prompt;
- item-side concentration, popularity, and coverage across aggregated recommendation lists;
- relevance controls to distinguish exposure shifts from utility collapse; and
- cross-metric analysis for concordant, independent, or inverse user/item fairness behavior.

No model is trained or fine-tuned. All model calls are local inference through Ollama.

## 2. Original engineering architecture

The initial architecture already separated the major responsibilities:

```text
datasets -> unified catalog -> personas/preferences -> prompt builder
        -> provider-independent model client -> parser/matcher
        -> append-only query records -> provider-free derived analysis
```

Important original principles were fixed preferences across counterfactual framings, a common
movie/music item schema, provider-independent clients, deterministic seeds, append-only Parquet,
resumability, pure metric functions, and separate collection and analysis.

The first frozen persona design, `persona-relevance-v1`, used six hand-specified preferences per
domain. Each preference was crossed with ten Big-Five poles, one shared neutral framing, and four
phrasing variants, producing 264 records per model/domain pilot. Movie relevance came from genre
rules; music relevance used listener-vector cosine similarity with the pre-results threshold 0.5.

## 3. Protocol-v1 diagnostic and why it was rejected

The first Qwen/movie run used a global candidate-pool architecture. It completed 264 records but
failed the grounding and opportunity controls:

| Diagnostic | Protocol-v1 result |
|---|---:|
| Mean matched items | 8.3258/10 |
| Exactly 10 matched | 34.85% |
| Hallucinated titles | 295 |
| Queries with hallucinations | 154 |
| Catalog-valid off-list titles | 116 |
| Queries with off-list titles | 57 |
| Relevant items available for M1-M6 | 3-26 |
| Runtime | 33.1 minutes |

No fairness-hypothesis output was inspected. The run was retained as diagnostic evidence and is
excluded from scientific and confirmatory results.

## 4. Closed-catalog-v2 architecture

The protocol was amended on 2026-08-01 before the other five model/domain pilots. The revised
architecture introduced:

- one deterministic 120-item candidate pool per base preference;
- the same pool across every trait and phrasing counterfactual;
- 60 head, 30 mid, and 30 tail candidates;
- at least 30 independently relevant candidates where available;
- deterministic display-order shuffling;
- coded entries formatted `C### | exact title`;
- an explicit instruction to choose only from the displayed catalog;
- full-catalog parsing that separates non-catalog hallucinations from catalog-valid off-list
  items; and
- protocol-versioned output roots so v1 records cannot be silently resumed or pooled.

The six-preference Qwen/movie technical check then matched 58/60 items with zero hallucinated or
off-list titles. All six closed-catalog-v2 scientific pilots subsequently passed, subject to the
model-specific caveats documented in `02_SIX_PILOT_TESTS.md`.

## 5. Grounding architecture corrections

Immutable raw responses exposed two parser/matcher issues rather than model failures:

1. Duplicate LastFM names could resolve to a catalog item outside the allowed pool before the
   allowed candidate ID was considered.
2. Llama often copied a valid allowed title and appended explanatory text, which a strict
   title-only matcher treated as part of the title.

The provider-free derived matcher was therefore versioned. The final pilot replay,
`allowed-title-annotation-v3`, accepts only an exact allowed title followed by an explicit
annotation delimiter. It does not accept invalid codes, truncated names, replacement lines, or
code/title mismatches. Raw records were not changed and models were not re-queried.

## 6. New 100-persona confirmatory architecture

The pilot's six preferences were adequate for feasibility but not an independent confirmatory
population. The new `persona-relevance-v2-100` architecture added:

- 100 independently constructed movie personas and 100 music personas;
- sampling without replacement from full datasets;
- disjoint preference-construction and held-out relevance-evaluation sets;
- stratification by activity, popularity tendency, and diversity;
- no raw user identifiers in prompts or public outputs;
- deterministic 120-item pools for every persona;
- versioned record provenance: design, bundle SHA256, dataset, and protocol;
- provenance-aware resume identities that reject legacy or mismatched records;
- deterministic per-partition query order;
- run manifests containing query-order digest, lockfile checksum, model digest, hardware, and
  attempt timestamps; and
- versioned analysis output roots.

The full matrix is 100 personas x 11 framings x 4 phrasings x 3 repeats = 13,200 records per
model/domain partition and 79,200 records across three models and two domains.

## 7. Phase E failure and amendment A1

The parent v2-100 balanced preflight made 84 calls covering all models, domains, traits, and
phrasings. Qwen and Gemma passed both domains, and Llama/movie passed. Llama/music produced at
least 10 grounded items on only 11/14 queries (78.6%), below the frozen 90% top-10 gate. The
bad-title rate was 0.72%. No fairness comparisons were computed.

Amendment A1 created `persona-relevance-v2-100-a1` and protocol
`closed-catalog-v2-a1-retry`. It leaves the first prompt unchanged at temperature 0.7. When the
first response grounds fewer than 10 items, the collector makes exactly one format-only retry at
temperature 0.0 using the same persona, trait wording, candidate pool, and order. It never retries
for taste, relevance, fairness, or item identity, and it accepts the second attempt even if still
short.

Every immutable row stores both attempts, both temperatures, the retry prompt, selected attempt,
and combined token/time accounting. The A1 Llama/music preflight reached 13/14 top-10 lists
(92.9%) and passed. Two responses retried; one reached 10 and one remained at 9.

## 8. Frozen architecture now in use

The active design has these identifiers:

| Component | Frozen value |
|---|---|
| Design | `persona-relevance-v2-100-a1` |
| Protocol | `closed-catalog-v2-a1-retry` |
| Bundle SHA256 | `f847715539c3d97c569cb597b9df50190c68be5bcd8eeb423f50871b84555d50` |
| Analysis version | `confirmatory-analysis-v1` |
| Personas | 100 per domain |
| Candidate pool | 120/persona: 60 head, 30 mid, 30 tail |
| Repeats | 3 |
| Partition size | 13,200 records |
| Total collection | 79,200 records |

The parent designs and pilot records remain immutable historical evidence. They must never be
merged into the A1 confirmatory collection.
