# Data, pipeline, metrics, and analysis

## 1. Data sources

| Domain/use | Dataset | Frozen archive checksum |
|---|---|---|
| Pilot movies | MovieLens 1M | MD5 `c4d9eecfca2ab87c1945afe126590906` |
| Full movies | MovieLens 25M | MD5 `6b51fb2759a8657d3bfcbfc42b592ada` |
| Pilot music/persona construction | LastFM-1K | MD5 `a79a6808f54f73354789a9fb02cb1e41` |
| Full music | LastFM-360K | MD5 `635e6ed3fc873aa4ba33aba0ebce02b1` |

Movie popularity is interaction/rating-count rank. Music popularity is play-count rank. Missing
music genre/provider data is not silently enriched in the primary analysis.

## 2. Unified item layer

Both domains map into a common item representation with item ID, domain, title, genres,
provider/studio when available, popularity rank and tier, and release year when available. Data
loaders validate uniqueness and schema before candidate construction.

## 3. Persona and preference controls

The base content preference is fixed across all personality and phrasing counterfactuals. Trait
language comes from documented Big-Five sources and is not presented as a diagnostic personality
scale. The neutral condition contains no personality sentence.

Four instruction phrasings—formal, casual, direct, and indirect—must pass semantic-equivalence
checks before collection. The persona ID and raw source-user ID are distinct; raw identifiers are
not allowed in prompts or public outputs.

## 4. Prompt and model layer

The prompt builder combines the fixed preference, one framing, one phrasing, the deterministic
candidate pool, and the coded closed-catalog instruction. Model clients share a single async
interface and return response text, token counts, timing, cost, and model snapshot. Provider
details do not leak into downstream analysis.

The current collection is Ollama-only. Cloud clients exist but are disabled and have no frozen
collection snapshots.

## 5. Parsing and grounding

The response parser extracts ranked coded/title entries. Grounding distinguishes:

- matched candidate items;
- non-catalog hallucinated titles; and
- catalog-valid items outside the allowed candidate pool.

Primary exposure uses grounded positions through rank 10. Overlong lists are truncated; short
lists remain short without imputation. Hallucinated and off-list entries are reported and
excluded from exposure counts.

Grounding can be replayed provider-free from immutable raw text and candidate IDs. Parser or
matcher corrections create a new derived grounding version and never mutate the raw record.

## 6. Immutable storage

Each completed query is one append-only Parquet record. The v2 schema includes:

- design, bundle, dataset, and protocol provenance;
- persona/model/domain/trait/level/phrasing/repeat identity;
- prompts and prompt SHA256;
- candidate and relevant item IDs;
- raw response and parsed titles;
- all response attempts and temperatures;
- selected attempt and retry prompt;
- matched, hallucinated, and off-list outputs; and
- token counts, cost, timestamp, and model snapshot.

Writes use a temporary Parquet file followed by atomic replacement. Existing query IDs are never
overwritten. Resume reads completed identities, validates provenance, and skips finished records.
An incompatible or duplicate design fails loudly.

## 7. Collection orchestration

The collection CLI validates the frozen design bundle and semantic phrasing, constructs the full
matrix, creates deterministic query order, checks the pilot-derived local cost gate, starts or
validates the run manifest, collects one model/domain partition, and marks the final attempt
completed only after all records are readable and one model digest is resolved.

Neutral prompts shared across traits may be queried once and materialized as separate condition
records. Only one writer may operate on a partition.

## 8. Metrics

### User-side

- Jaccard harm (`1 - Jaccard@10`) is the primary outcome relative to the paired neutral list.
- SNSR, SNSV, PAFS, SERP harm, and PRAG harm are supported secondary views.

### Item-side

- Exposure Gini.
- Herfindahl-Hirschman Index (HHI).
- Catalog coverage.
- Average Recommendation Popularity at 10 (ARP@10).
- Long-tail coverage, MGU, and DGU as secondary outcomes.

### Utility controls

- Precision@10.
- NDCG@10.

All metrics are derived after collection. Metric functions do not call providers and do not
write raw query data.

## 9. Statistical contract

- Domain-specific mixed models are primary; pooled-domain models are secondary.
- Trait, level, phrasing, and model are fixed effects; persona has a random intercept.
- Aggregate item metrics and trait-minus-neutral deltas use 2,000 persona-cluster bootstrap
  resamples with 95% intervals.
- Benjamini-Hochberg correction at q=0.05 is applied separately within domain, model, metric
  family, and planned contrast family.
- Both raw and adjusted p-values are retained.
- Effects below the 0.20 standardized SESOI are scientifically negligible even if statistically
  distinguishable.

RQ3 orients metrics as harm and uses Spearman rank correlation:

- Concordant: rho >= 0.20 and adjusted p < 0.05.
- Inverse: rho <= -0.20 and adjusted p < 0.05.
- Independent: otherwise.
- Constant-input correlations remain explicitly undefined.

## 10. Sensitivity analyses

- Primary: all grounded positions through rank 10, no imputation.
- Exact-10-only sensitivity view.
- Sensitivity excluding conservatively flagged entries.
- Report exposure yield and exact-10 yield by partition and condition.

## 11. Analysis output order

After all partitions are frozen:

1. lock/checksum raw partitions;
2. re-ground using the versioned matcher;
3. generate collection diagnostics and relevance controls;
4. compute user-side, item-side, utility, and paired-delta tables;
5. run cluster bootstrap and mixed models;
6. apply correction families;
7. produce RQ3 scenarios;
8. check convergence, residuals, missing exposure, and sensitivity views; and
9. freeze manuscript tables/figures under an analysis-version hash.
