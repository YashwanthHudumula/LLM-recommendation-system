# Manuscript asset freeze v1

Freeze date: **2026-08-25**  
Asset version: `manuscript-assets-v1`  
Classification: deterministic publication asset package derived from frozen v2/v3 evidence

## 1. Outcome

The first manuscript-ready evidence package is complete. It contains five figure sets in PDF,
SVG, and 400-DPI PNG, plus five tables in CSV and LaTeX. The 26 generated assets are governed by
a write-once specification, independently checksummed, visually inspected, and reproduced in a
second destination with 26/26 identical content hashes.

This gate freezes presentation, not scientific conclusions. Figures and tables summarize
already-frozen analyses; no model queries or new outcome analyses were performed. Corrections
require a new asset version rather than manual editing.

## 2. Frozen inputs and controls

The renderer verifies both evidence audits before reading an analysis table:

| Evidence | SHA-256 |
|---|---|
| Confirmatory v2 audit | `b7193059e3c3c7b200863d5a2f084b3b46748a62a8cb36f154e3ae22ad3e65da` |
| Opportunity v3 audit | `2d43b34f566d68432510e959e49d6589b5378dc96d84f91839b13640735570bc` |

The frozen specification is `config/manuscript_assets_v1.yaml`, SHA-256
`135ed2f3f49247a8232f6899b19770379f55824234900249cb06260729fa12da`.
It fixes asset names, formats, raster resolution, font family, and source audits. The renderer
refuses a non-empty output directory and verifies exact agreement between output names and the
specification.

## 3. Figure set

1. **Relevance-exposure opportunity trade-off** plots Precision@10 against opportunity-adjusted
   catalog coverage for every condition, with model means highlighted by domain.
2. **Opportunity delta forest** reports the largest absolute observed Gini and coverage delta
   for each model/domain with persona-bootstrap 95% confidence intervals. These maxima are
   explicitly labeled descriptive and not multiplicity-adjusted discoveries.
3. **RQ3 scenario composition** counts Concordant, Independent, Inverse, and Undefined
   user-side/item-side metric relationships for each model/domain.
4. **Raw-adjusted concordance** compares raw and eligibility-adjusted deltas for Gini, HHI,
   catalog coverage, and long-tail coverage, with domain-specific Spearman rho.
5. **Sensitivity concordance (Figure S1)** shows primary-versus-exact-10 and
   primary-versus-unflagged rank and sign agreement for all five opportunity metrics.

Visual QA rejected the first render for title/legend overlap, a clipped label, ambiguous domain
abbreviations, and crowded scientific tick labels. A layout-only correction was rerendered and
all final PNGs were inspected at original resolution. No values or asset selection changed.

## 4. Table set

1. **Study design** records 39,600 queries per domain, sensitivity retention, and eligible
   catalog size (935 movie items; 2,516 music artists).
2. **Primary model summary** combines relevance, list similarity, raw concentration/coverage,
   and opportunity-adjusted concentration/coverage by model/domain.
3. **Opportunity delta summary** records delta magnitude, intervals excluding zero, and
   exact-10/unflagged concordance for every opportunity metric and domain.
4. **RQ3 scenarios** supplies the exact counts used by Figure 3.
5. **Strongest opportunity effects** supplies the point estimates and bootstrap intervals used
   by Figure 2.

Notable presentation-level summaries include:

- Exact-10 retention is 83.68% for movie and 90.03% for music; unflagged retention is 97.32%
  and 99.89%, respectively.
- Mean model-level opportunity coverage ranges from 0.257 to 0.415 in movie and 0.212 to 0.331
  in music.
- Coverage deltas have 30/120 movie and 44/120 music bootstrap intervals excluding zero; Gini
  deltas have 28/120 and 47/120. These descriptive counts do not replace corrected inference.
- Exact-10 concordance is materially weaker in music (rho 0.26-0.68), while the unflagged view
  is highly concordant in both domains (rho 0.98-1.00).

## 5. Verification record

| Check | Result |
|---|---|
| Source audit verification | 2/2 exact hashes |
| Generated content | 26 assets plus manifest |
| Figures | 5 PDF, 5 SVG, 5 PNG |
| Tables | 5 CSV, 5 LaTeX, plus notes |
| SVG parsing | 5/5 valid XML |
| PDF structural markers | 5/5 valid header and EOF markers |
| Visual inspection | 5/5 accepted after layout correction |
| Deterministic rerender | 26/26 content hashes identical |
| Independent inventory | 26/26 files verified |

The package manifest is
`outputs/manuscript_assets/version=manuscript-assets-v1/manifest.json`, SHA-256
`741e73b19e64f6311e497feafaee8e2d5eb9f0100caaa296a9d23d31f7cdb20c`.
The tracked independent audit is
`data/audits/manuscript_assets_v1_reproducibility.json`, SHA-256
`3cc96ac5664c8b230b60d4eccad169282e049d1b7f6e5088e1ceb4b3e0e479bc`.

## 6. Reproduction

```powershell
uv run recllm-build-manuscript-assets
uv run python preservation/summarize_manuscript_assets_v1.py
```

The build is intentionally write-once. For a determinism check, pass `--output-root` with an
empty temporary destination and compare content hashes.

## 7. Remaining publication gates

Next is manuscript drafting against these frozen assets. Bibliography/DOI verification, journal
selection and formatting, author metadata, reporting/ethics checklists, and external archival
deposition with a DOI remain open. The repository is evidence- and asset-ready, but not yet
submission-ready.
