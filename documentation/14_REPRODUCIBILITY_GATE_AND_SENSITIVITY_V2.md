# Reproducibility gate and registered sensitivity analysis v2

**Gate date:** 2026-08-25

**Frozen design:** `persona-relevance-v2-100-a1`

**Collection protocol:** `closed-catalog-v2-a1-retry`

**Analysis family:** `confirmatory-analysis-v2`
**Source:** 79,200 immutable query records; 39,600 per domain

## Outcome

The clean-environment provider-free replay, both registered sensitivity views, and statistical
fit remediation are complete. All six analysis packages are checksummed. This closes the
reproducibility and registered-sensitivity portion of Gate G, but does not by itself make the
paper submission-ready: within-candidate-opportunity metrics, final figures, manuscript text,
source verification, and external archival deposition remain.

## Clean environment and software gate

The unavailable historical `.venv` referenced a removed Python installation. It was preserved
unchanged, and a new `.venv-repro` was built from `uv.lock` with CPython 3.12.5 and the locked dev
extra. The lockfile SHA-256 is
`99687297f3fad09232d43cde627f589eede5eea8e879e18be50c5e94ccc22a51`.

Final verification:

- `pytest`: 48/48 passed;
- strict `mypy`: no issues in 60 source files;
- Ruff lint: passed;
- Ruff format check: 76 files formatted;
- sensitivity CLI help/runtime validation: passed.

The reader now prunes `model` and `domain` partitions before opening Parquet files. A regression
test proves that an unreadable file in an excluded domain is never opened. This changes only I/O
selection; post-read column filtering remains in place as a correctness backstop.

## Completed analysis packages

| Domain | View | Source rows | Retained paired-complete rows | Retention |
|---|---|---:|---:|---:|
| Movie | Primary | 39,600 | 39,600 | 100.00% |
| Movie | Exact 10 grounded | 39,600 | 33,139 | 83.68% |
| Movie | Exclude flagged records | 39,600 | 38,539 | 97.32% |
| Music | Primary | 39,600 | 39,600 | 100.00% |
| Music | Exact 10 grounded | 39,600 | 35,653 | 90.03% |
| Music | Exclude flagged records | 39,600 | 39,556 | 99.89% |

Sensitivity filters are applied only after provider-free re-grounding. A sensitive record is
retained only when its corresponding neutral key also survives the same view. An initial
exact-10 attempt correctly failed because independent row filtering could orphan a sensitive
record; it wrote no tables. Pair-complete filtering was then implemented and regression-tested
before the final immutable sensitivity packages were run.

## Primary-versus-sensitivity concordance

The machine-readable comparison aligns every condition and measures Spearman correlation and
sign agreement for trait-minus-neutral item deltas, plus scenario agreement for all 81 RQ3 rows
per domain.

| Domain | View | Minimum item-delta rho | Minimum sign agreement | Minimum user-metric rho | RQ3 agreement |
|---|---|---:|---:|---:|---:|
| Movie | Exact 10 grounded | 0.79 | 0.85 | 0.99 | 74/81 (91.36%) |
| Movie | Exclude flagged | 0.99 | 0.95 | 1.00 | 80/81 (98.77%) |
| Music | Exact 10 grounded | 0.40 | 0.80 | 1.00 | 78/81 (96.30%) |
| Music | Exclude flagged | 1.00 | 0.99 | 1.00 | 80/81 (98.77%) |

The low music exact-10 minimum is catalog-coverage delta (`rho=0.40`); ARP and HHI remain at
`rho=0.99`, Gini at `rho=0.85`, and popularity MGU/DGU at `rho=0.94/0.95`. Music genre MGU/DGU
are constant zero under the frozen no-enrichment rule, so their correlations are undefined.

The exact-10 scenario changes are concentrated in Llama. Movie changes six Llama
popularity-MGU/DGU correlations from Concordant to Independent and one PRAG/long-tail result from
Independent to Inverse. Music changes two Llama popularity results from Concordant to Independent
and the Qwen Jaccard/ARP result from Inverse to Independent. These are material robustness
qualifications and must be reported, not averaged away. Excluding flagged records changes only
one RQ3 scenario per domain.

## Singular-fit diagnosis and transparent alternative

`converged=True` did not clear the preregistered MixedLM fits. Every successful primary fit
reported singular random-effects covariance, boundary estimates, and a non-positive-definite
Hessian. Hard failures also depend on the derived view:

| Domain | View | MixedLM hard failures | Outcomes carrying warnings |
|---|---|---:|---:|
| Movie | Primary | 0 | 6 |
| Movie | Exact 10 grounded | 0 | 6 |
| Movie | Exclude flagged | 3 item-side | 3 user-side |
| Music | Primary | 3 item-side | 3 user-side |
| Music | Exact 10 grounded | 3 item-side | 3 user-side |
| Music | Exclude flagged | 0 | 6 |

The failed and warned MixedLM tables remain untouched. As a transparent diagnostic alternative,
each package now includes OLS fixed effects with standard errors clustered by the 100 independent
personas. Coefficients are standardized by the fitted residual SD and compared with the frozen
0.20-SD SESOI. All 72 coefficient rows per domain/view were produced with zero failures. These
cluster-robust estimates are sensitivity evidence, not an undisclosed replacement for the
preregistered model.

## Provenance and hashing

`data/audits/confirmatory_analysis_v2_reproducibility.json` contains:

- the base Git commit and lockfile SHA-256;
- source and retained counts for all six packages;
- MixedLM and cluster-robust fit summaries;
- primary-versus-sensitivity concordance for every metric;
- all RQ3 scenario changes; and
- path, byte size, and SHA-256 for 90 analysis files.

The earlier historical analysis directory from the former account was unavailable, so a
byte-for-byte comparison with those 26 files could not be performed. The clean replay reproduces
the documented table shapes, primary row counts, undefined music correlations, singular warnings,
and missing music item-side MixedLM behavior. The new v2 packages are the authoritative replay.

The complete workspace was also copied to `E:\Post_phase_1_LLM_recc`. The independent archive
verification checked all 90 analysis files against the audit inventory: 90 verified, zero missing,
zero size mismatches, and zero hash mismatches. Its receipt is stored in that archive at
`preservation/analysis_v2_copy_receipt.json`.

## Reproduction commands

```powershell
$env:UV_PROJECT_ENVIRONMENT = ".venv-repro"
uv sync --locked --extra dev --python 3.12.5

uv run recllm-analyze --config-dir config `
  --config-override config/full_run_v2_100_a1.yaml `
  --stage full --domain movie --analysis-version confirmatory-analysis-v2

uv run recllm-analyze --config-dir config `
  --config-override config/full_run_v2_100_a1.yaml `
  --stage full --domain movie `
  --analysis-version confirmatory-analysis-v2-sensitivity-exact10 `
  --sensitivity exact-10-grounded

uv run recllm-analyze --config-dir config `
  --config-override config/full_run_v2_100_a1.yaml `
  --stage full --domain movie `
  --analysis-version confirmatory-analysis-v2-sensitivity-unflagged `
  --sensitivity exclude-flagged-records

uv run python -m recllm_fairness.pipeline.run_fit_diagnostics `
  outputs/tables/analysis/<analysis-package>

uv run python preservation/summarize_analysis_v2.py
```

Repeat the analysis commands with `--domain music`. Output directories are write-once; use a new
analysis version rather than overwriting a completed package.

## Remaining publication gates

1. Add the registered within-candidate-opportunity coverage/concentration sensitivity metrics.
2. Produce residual and influence diagnostics for the cluster-robust alternatives.
3. Freeze manuscript tables and figures from the checksummed v2 packages.
4. Verify every related-work claim and bibliography record against primary sources.
5. Draft the methods, results, ethics, limitations, and data-availability sections.
6. Deposit permitted code/evidence in an external archival repository and mint a DOI.
