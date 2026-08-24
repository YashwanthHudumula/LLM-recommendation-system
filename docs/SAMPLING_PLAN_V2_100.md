# Frozen confirmatory sampling and analysis plan

**Design:** `persona-relevance-v2-100`
**Frozen:** 2026-08-03, before confirmatory collection
**Researcher confirmation:** "proceed" after presentation of the recommended SESOI
**Status:** frozen

## Sampling design

- 100 independently constructed personas per domain, sampled without replacement.
- Two domains: MovieLens 25M movies and LastFM-360K artists.
- Ten Big-Five trait poles, one shared neutral baseline, and four phrasing variants.
- Three stochastic repeats per prompt condition. Repeats estimate decoding variability and
  are not additional independent personas.
- 4,400 prompt conditions and 13,200 records per model/domain partition; 79,200 records total.
- One fixed 120-item pool per persona with 60 head, 30 mid, and 30 tail items and at least 30
  held-out relevant items.

## Smallest effect of scientific interest and precision

The confirmatory SESOI is an absolute standardized within-persona trait-pole versus neutral
effect of **0.20 residual standard deviations**. Effects smaller than this are interpreted as
scientifically negligible even if statistically distinguishable.

The pre-results simulation used 200 datasets, 100 personas, four phrasings, three repeats,
random-intercept SD 0.50, residual SD 1.0, and alpha 0.05. It produced power 1.00, mean 95% CI
width 0.1601, median standard error 0.0409, convergence 1.00, and failure rate 0.00. The frozen
machine-readable report is `data/audits/power_precision_v2_100.json`.

## Outcomes and models

Primary user-side outcome: Jaccard harm (`1 - Jaccard@10`) relative to the paired neutral list.
Primary item-side outcomes: exposure Gini, HHI, catalog coverage, and ARP@10. Precision@10 and
NDCG@10 are primary utility controls. SERP/PRAG harm, long-tail coverage, MGU, and DGU are
secondary outcomes.

Persona-level outcomes use mixed models with trait, trait level, phrasing, and model as fixed
effects and a persona random intercept. Domain-specific models are primary; pooled-domain
models are secondary. Aggregate item metrics and trait-minus-neutral deltas use 2,000
persona-cluster bootstrap resamples at the frozen project seed and 95% intervals.

Benjamini-Hochberg correction at q=0.05 is applied separately within each domain, model,
metric family (user-side, item-side, utility), and planned trait-pole contrast family. Raw and
adjusted p-values are both reported.

RQ3 orients all metrics as harm and uses Spearman rank correlation. A result is Concordant when
rho >= 0.20 and adjusted p < 0.05, Inverse when rho <= -0.20 and adjusted p < 0.05, and
Independent otherwise. Undefined constant-input correlations remain explicitly undefined.

## List handling and sensitivity analyses

- Primary analysis uses grounded positions through rank 10 without imputation.
- Overlong lists are truncated to 10; short lists remain short.
- Exposure yield and exact-10 yield are reported for every partition and condition.
- Sensitivity views require exactly 10 grounded items and separately exclude conservatively
  flagged entries.
- Hallucinated and catalog-valid off-list items are reported but excluded from exposure counts.
- Raw responses remain immutable; grounding corrections create a new derived version.

## Operational pause gates

These gates are evaluated without inspecting trait-level fairness outcomes. Pause a partition
and diagnose before continuing if any occurs:

- model digest differs from the configured immutable digest;
- unique-record count, repeat count, prompt hash, design hash, or resume identity fails;
- fewer than 95% of records yield at least one grounded item;
- fewer than 90% of records yield exactly 10 grounded positions;
- hallucination plus off-list rate exceeds 2% of parsed titles;
- a write, manifest, interruption/resume, thermal, or storage-integrity check fails.

No threshold, outcome, model formula, exclusion, or correction family may be changed after
confirmatory output is inspected under this design version. Corrections require a new version
