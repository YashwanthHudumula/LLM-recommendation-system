# Reproducible experiment protocol

## 1. Freeze the design

Build labels with `uv run recllm-build-labels --stage pilot`. Review the combined draft bundle,
complete the documented cooling-off and independent blind wording checks, change the design
status only after those checks pass, and regenerate the bundle. Record its SHA256 and commit it
before any real model call. Archive the proposal, commit hash, `uv.lock`, all configuration
files, current date, provider/model snapshot IDs, prices, and API-region information. Never
replace a snapshot ID in an existing run; add a new model key.

Each domain has six fixed base preferences. Every base preference is crossed with ten Big-Five
poles plus one shared neutral baseline and the configured phrasing variants. Movie relevance is
the complete declared genre-filter set with at least 20 ratings. Music relevance uses binary
listener-vector cosine similarity to the declared seed-union, at least 30 listeners, and the
pre-results selected threshold recorded in the versioned design.

## 2. Verify data

Download the four archives listed in `data/DATA_SOURCES.md`, compare MD5 checksums, and
extract to the configured roots. MovieLens ratings become movie interaction counts. LastFM-1K
events and LastFM-360K play counts both become artist-level interaction counts. Do not enrich
missing music genres/providers during the primary analysis unless the enrichment source,
version, matching yield, and license are frozen in a separate provenance record.

## 3. Validate phrasing before any paid call

The real collection command loads the configured sentence-transformer and computes every
pairwise cosine similarity among formal, casual, direct, and indirect instructions. One pair
below the configured threshold aborts collection. Record the complete pairwise table in the
run log.

## 4. Pilot the exact model/domain

The synthetic `recllm-pilot` command is a software smoke test only. A scientific pilot uses:

```powershell
uv run recllm-collect --model MODEL_KEY --domain movie --stage pilot
```

This produces a model/domain-specific cost estimate. Inspect parse yield, hallucination rate,
off-list rate, list length, token counts, and cost. Fix parsing or prompt defects before full
collection; do not silently mix pre-fix and post-fix records under one run identity.

## 5. Full collection

```powershell
uv run recllm-collect --model MODEL_KEY --domain movie --stage full
```

Full collection refuses to start without the matching pilot estimate or if projected spend
exceeds the hard cap. Identical neutral prompts shared across traits are queried once per
repeat and materialized as separate condition records with cost charged only to the source
record. Restarting checks the complete experimental identity and skips finished records.

Run each provider/domain separately. Never run multiple collectors against the same output
partition concurrently.

## 6. Analysis

Analysis reads only immutable Parquet records; it imports no provider client. To combine
models for one domain, point `--query-root` to their common ancestor and select `--domain`.

```powershell
uv run recllm-analyze --query-root outputs/queries/full --domain movie
```

Review, in order: collection diagnostics, relevance availability, published user-side sanity
checks, group exposure shares, item metric deltas, paired bootstrap intervals, mixed-model
convergence/warnings, corrected p-values, and RQ3 scenarios. An undefined correlation from
constant ranks is reported as undefined rather than relabeled “independent.”

## 7. Mitigation

Mitigation is blocked until the primary item-side table exists. It writes to a separate root,
uses the identical population and candidates, adds only the declared fairness system-role
instruction, and accounts for earlier full-run spend under the same hard cap.

## 8. Reporting checklist

- Report exact model snapshots and collection timestamps, not provider family names alone.
- Report candidate-pool construction and both catalog and matched-list sizes.
- Report hallucination and off-list rates by condition.
- Report estimates with persona-bootstrap intervals, corrected p-values, and effect sizes.
- Separate confirmatory outcomes from exploratory genre/provider slices.
- Describe patterns as behavior of these model snapshots and datasets, never as truths about
  personality groups.
- Archive de-identified raw model text only where provider terms and dataset licenses allow.
