# Within-candidate-opportunity sensitivity analysis v3

**Completion date:** 2026-08-25

**Analysis family:** `confirmatory-analysis-v3-opportunity`

**Operational protocol:** `within-candidate-opportunity-v1`

**Classification:** post-collection, protocol-aligned sensitivity

## Outcome

Adjusting each item's exposure for how often it was actually eligible does not remove the main
exposure-disparity signal. Candidate opportunity therefore cannot by itself explain the observed
trait-minus-neutral shifts. Coverage results are essentially unchanged, while concentration
results remain directionally related but are less interchangeable with the original full-catalog
metrics.

This analysis closes the within-opportunity publication gate identified in the v2 reproducibility
report. It does not turn the project into a submission-ready paper by itself; figures, manuscript
text, primary-source bibliography verification, and external archival deposition still remain.

## Why this sensitivity was needed

Every persona sees a fixed 120-item pool, but the union of those pools is much smaller than the
complete MovieLens or LastFM catalog. Full-catalog Gini and coverage consequently include many
items that could never have been selected in a condition. The v3 analysis separates unequal
model selection from unequal item eligibility.

The original proposal required fixed candidate pools but did not provide a mathematical
definition for a within-opportunity concentration measure. The operational definition was frozen
in `config/opportunity_sensitivity_v1.yaml` before v3 results were inspected. It is described as
protocol-aligned and post-collection, not as a prospective preregistration.

## Frozen definition

For item (i) and condition (c):

- (E_{ic}) is the number of top-10 lists containing the item;
- (O_{ic}) is the number of queries whose candidate pool contains the item; and
- (R_{ic}=E_{ic}/O_{ic}) is its selection rate conditional on eligibility.

The eligible universe contains every item with (O_{ic}>0). The five reported metrics are:

1. Gini over the vector of item selection rates (R_{ic}), including eligible items with zero
   exposure.
2. HHI after normalizing the selection-rate vector to sum to one.
3. Zero-to-one normalized HHI, allowing comparison across eligible-universe sizes.
4. Opportunity coverage: the fraction of eligible items with positive exposure.
5. Opportunity long-tail coverage: the same fraction restricted to eligible tail items.

Trait-minus-neutral differences use the matched model/domain/phrasing neutral condition.
Uncertainty uses paired persona resampling: 2,000 draws for primary views and 500 draws for the
exact-10 and unflagged robustness views. Repeats stay clustered inside their persona.

## Data reconstruction validation

The movie primary analysis was replayed directly from all 39,600 immutable records, including
provider-free re-grounding. Its full run completed in 2,841.6 seconds. The remaining packages use
the checksummed v2 `user_side_similarities.csv` tables, which already contain each regrounded
sensitive row, its candidate pool, and its matched neutral list.

For every domain/view, sensitive rows plus unique neutral pairs exactly reconstruct the manifest
query count:

| Domain/view | Manifest rows | Sensitive rows | Neutral pairs | Reconstructed rows |
|---|---:|---:|---:|---:|
| Movie primary | 39,600 | 36,000 | 3,600 | 39,600 |
| Movie exact 10 | 33,139 | 29,891 | 3,248 | 33,139 |
| Movie unflagged | 38,539 | 34,991 | 3,548 | 38,539 |
| Music primary | 39,600 | 36,000 | 3,600 | 39,600 |
| Music exact 10 | 35,653 | 32,233 | 3,420 | 35,653 |
| Music unflagged | 39,556 | 35,956 | 3,600 | 39,556 |

As an independent acceptance check, opportunity metrics reconstructed from the movie v2 paired
table were compared with the raw-record v3 replay. All 132 condition rows matched; the largest
floating-point difference across all nine output fields was below `1e-16`.

## Primary absolute results

The eligible union is constant across primary conditions: 935 movie items and 2,516 music items.
Model-level condition means are:

| Domain | Model | Opportunity Gini | Normalized HHI | Coverage | Tail coverage |
|---|---|---:|---:|---:|---:|
| Movie | Gemma 3 12B | 0.8357 | 0.00518 | 0.3125 | 0.1484 |
| Movie | Llama 3.1 8B | 0.7711 | 0.00357 | 0.4147 | 0.4121 |
| Movie | Qwen 3 8B | 0.8693 | 0.00729 | 0.2572 | 0.2307 |
| Music | Gemma 3 12B | 0.8519 | 0.00205 | 0.2500 | 0.2562 |
| Music | Llama 3.1 8B | 0.7917 | 0.00143 | 0.3309 | 0.4609 |
| Music | Qwen 3 8B | 0.8795 | 0.00264 | 0.2120 | 0.3044 |

Llama exposes the broadest eligible set and has the lowest adjusted concentration in both
domains. Qwen has the highest adjusted Gini and lowest opportunity coverage. These are
descriptive model comparisons, not causal claims about model families generally.

## Trait-minus-neutral shifts

Across 120 sensitive conditions per domain, mean absolute deltas were:

| Domain | Gini | Normalized HHI | Coverage | Tail coverage |
|---|---:|---:|---:|---:|
| Movie | 0.00917 | 0.000383 | 0.01398 | 0.02547 |
| Music | 0.00759 | 0.000128 | 0.01066 | 0.02277 |

Unadjusted 95% paired-bootstrap intervals excluded zero for the following number of contrasts:

| Domain | Gini | HHI | Normalized HHI | Coverage | Tail coverage |
|---|---:|---:|---:|---:|---:|
| Movie | 28/120 | 24/120 | 24/120 | 30/120 | 11/120 |
| Music | 47/120 | 45/120 | 45/120 | 44/120 | 16/120 |

These counts summarize sensitivity strength and are not multiplicity-corrected discovery tests.
The manuscript must emphasize effect sizes, paired intervals, and the existing corrected models
rather than treating the counts as a new hypothesis-testing family.

Illustrative largest shifts include movie Llama low-openness/casual Gini `+0.0363` with a 95%
interval `[+0.0145,+0.0447]`, and coverage `-0.0599` with interval
`[-0.0675,-0.0274]`. In music, Llama high-agreeableness/direct Gini is `-0.0210`
`[-0.0310,-0.0067]`, while Qwen low-openness/indirect normalized HHI is `+0.000518`
`[+0.000339,+0.001011]`.

## Agreement with full-catalog results

Coverage deltas are effectively invariant to the denominator change:

| Domain | Metric | Spearman rho | Sign agreement |
|---|---|---:|---:|
| Movie | Catalog/opportunity coverage | 0.99996 | 100.0% |
| Movie | Tail coverage | 0.99780 | 100.0% |
| Music | Catalog/opportunity coverage | 0.99995 | 100.0% |
| Music | Tail coverage | 0.99914 | 100.0% |

Concentration agreement is moderate rather than exact. Raw-versus-adjusted Gini rho is 0.754
for movies and 0.830 for music, with sign agreement of 76.7% and 81.7%. HHI rho is 0.456 and
0.611, with sign agreement of 64.2% and 69.2%. The adjusted metrics should therefore be reported
alongside—not substituted silently for—the original estimands.

## Robustness views

The unflagged view closely reproduces primary opportunity deltas. Across metrics, rho ranges from
0.983 to 0.995 for movies and 0.997 to 0.999 for music; sign agreement is at least 94.2% and
98.3%, respectively.

Exact-10 filtering is less stable. Movie rho ranges from 0.704 to 0.836 with 81.7–90.8% sign
agreement. Music rho ranges from 0.261 to 0.683 with 80.0–83.3% sign agreement. This reinforces
the v2 conclusion that literal list-length adherence is a material sensitivity, especially for
music, and must remain visible in the paper.

## Reproducibility artifacts

`data/audits/opportunity_analysis_v3_reproducibility.json` records:

- the frozen protocol path and SHA-256;
- six package manifests and retained query counts;
- absolute model means and delta magnitudes;
- paired interval counts;
- raw-versus-adjusted and primary-versus-sensitivity concordance; and
- SHA-256 and byte size for 36 v3 analysis files.

The complete workspace was synchronized to `E:\Post_phase_1_LLM_recc`. Independent verification
against the audit inventory confirmed 36/36 v3 files, with zero missing, size-mismatched, or
hash-mismatched artifacts. The archive receipt is
`preservation/opportunity_v3_copy_receipt.json` inside that copy.

The opportunity-only runner accepts a frozen v2 analysis package and refuses count mismatches:

```powershell
uv run recllm-opportunity-analyze `
  outputs/tables/analysis/<frozen-v2-package> `
  --config-dir config `
  --config-override config/full_run_v2_100_a1.yaml `
  --analysis-version confirmatory-analysis-v3-opportunity `
  --bootstrap-resamples 2000

uv run python preservation/summarize_opportunity_v3.py
```

Completed output directories remain write-once. New reruns must use a new analysis version.

## Remaining publication gates

1. Produce the frozen manuscript table and figure package from the v2/v3 checksummed evidence.
2. Verify related-work claims and bibliography records against primary publications.
3. Draft methods, results, ethics, limitations, and data/code-availability sections.
4. Deposit the permitted replication package in an archival repository and mint a DOI.
