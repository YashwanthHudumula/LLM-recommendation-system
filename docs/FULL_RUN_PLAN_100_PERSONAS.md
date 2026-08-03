# Full-run plan: 100 independent personas per domain

**Decision date:** 2026-08-02
**Status:** Phase A passed; population construction and design-v2 freeze pending
**Scope:** 100 movie personas, 100 music personas, three model snapshots, three repeats

## 1. Confirmatory matrix

Each independent base persona is crossed with 10 Big-Five trait poles, one shared neutral
baseline, and four phrasing variants. The full design therefore contains:

| Unit | Records |
|---|---:|
| One persona, one model, one domain, three repeats | 132 |
| One model/domain partition | 13,200 |
| One domain across three models | 39,600 |
| Complete two-domain, three-model collection | 79,200 |

The 100 personas must be genuinely distinct, independently constructed preference profiles.
Repeating, renaming, or lightly paraphrasing the six pilot preferences does not increase the
independent sample size.

## 2. Phase A - amend and version the protocol

- [x] Create `persona-relevance-v2-100` without changing or overwriting frozen v1 artifacts.
- [x] Add `design_version`, design-bundle SHA256, dataset version, and collection-protocol
  version to every immutable query record and its resumability identity.
- [x] Put v2 records and analyses under versioned roots so v1 pilot rows cannot be mixed with
  the confirmatory population.
- [x] Version analysis tables by design, domain, model set, and analysis version to prevent
  later replays from overwriting manuscript evidence.
- [x] Deterministically randomize query order within each model/domain partition and store a
  run manifest containing seed, environment lock hash, model digest, start/end time, and host
  hardware.
- [x] Add migration/regression tests proving that v1 remains readable while v2 cannot resume
  from an incompatible design.

**Gate A:** tests, lint, and strict typing pass; an intentional v1/v2 resume attempt fails.

Gate A passed on 2026-08-03: 41 tests passed, lint reported no findings, strict typing passed
across 56 source files, the dependency lock remained current, and the regression suite rejected
both legacy-to-v2 and mismatched-bundle resume attempts. The v2 override remains deliberately
blocked while its design status is `draft` and bundle hash is unset.

## 3. Phase B - construct the independent population

Construct profiles algorithmically from the full datasets rather than inventing 188 cosmetic
variants of the existing preferences.

### Movies: MovieLens 25M

- Select 100 distinct eligible users without replacement using the frozen project seed.
- Determine eligibility from a pre-results feasibility sweep: enough positively rated movies
  to create disjoint preference-construction and relevance-evaluation sets, with at least 30
  relevant candidate items after the split.
- Stratify selection on activity, popularity tendency, and genre diversity so the sample does
  not consist only of highly active mainstream users.
- Derive each stated preference from only the construction split using a controlled template
  and fixed genre/era features; do not use an LLM to improvise preference text.
- Define relevance only from the held-out positive-rating split. Do not use demographic fields.

### Music: LastFM-360K

- Select 100 distinct eligible listeners without replacement using the same frozen procedure.
- Require enough distinct artists for disjoint construction and evaluation sets and at least
  30 held-out relevant artists.
- Stratify on activity, popularity tendency, and listening diversity.
- Create the stated preference from construction-only seed artists using a controlled template.
- Define relevance from held-out listened artists; keep raw listener identifiers out of prompts
  and public outputs.

The exact rating threshold, activity threshold, split fraction, strata boundaries, and template
grammar must be chosen from dataset feasibility diagnostics only and frozen before any v2 model
output is collected.

**Gate B:** exactly 100 unique profile IDs per domain; no construction/evaluation leakage; no
duplicate profile records; every profile has sufficient relevant opportunity.

## 4. Phase C - justify and freeze the sampling plan

- [ ] Define the smallest effect size of scientific interest before confirmatory results.
- [ ] Run mixed-model simulation/precision checks for the chosen 100-persona design and record
  power, expected confidence-interval width, convergence, and failure rates.
- [ ] Retain three stochastic repeats; repeats estimate decoding variability and are not counted
  as additional personas.
- [ ] Predeclare primary outcomes, model formulae, 2,000 persona-cluster bootstrap resamples,
  Benjamini-Hochberg families, and RQ3 classification thresholds.
- [ ] Predeclare list handling: primary analysis uses grounded positions up to rank 10 without
  imputation; overlong lists are truncated to 10. Report exposure yield. Run an exact-10
  sensitivity view and a sensitivity view excluding conservatively flagged entries.
- [ ] Predeclare operational pause thresholds without inspecting fairness outcomes: pause a
  partition if format yield, off-list rate, or model snapshot validation breaches its gate.

**Gate C:** signed/frozen sampling-plan document and a new immutable design-bundle SHA256.

## 5. Phase D - build and audit v2 artifacts

- [ ] Generate 100 full-stage relevance-label records per domain.
- [ ] Build one deterministic 120-item candidate pool per persona, preserving the 50/25/25
  head/mid/tail opportunity mix and at least 30 relevant items where feasible.
- [ ] Verify stable IDs, unique candidate entries, display-order randomization, full-catalog
  grounding, counterfactual preference invariance, and semantic phrasing equivalence.
- [ ] Produce de-identified population, label, candidate-pool, and exclusion audit tables.
- [ ] Perform a human review of a random, seed-fixed profile sample for natural wording and
  absence of personality/taste leakage.

**Gate D:** all automated audits pass and the reviewed v2 bundle is frozen. No wording or label
changes are permitted under the same version after this point.

## 6. Phase E - no-cost preflight and duration check

- [ ] Verify all three Ollama digests on the execution machine.
- [ ] Run a balanced seed-fixed preflight covering all traits, phrasings, domains, and a sample
  of the new candidate pools. Do not inspect fairness comparisons.
- [ ] Confirm parsing, top-10 yield, hallucination/off-list separation, resumability, storage
  throughput, thermals, and projected duration.
- [ ] Deliberately interrupt and resume a disposable preflight partition.

**Gate E:** no snapshot mismatch, no resumability failure, and all predeclared quality thresholds
pass.

## 7. Phase F - full collection

Run only one model/domain writer at a time. Each completed partition must contain 13,200 unique
records before proceeding. The recommended six-part sequence is determined and recorded once
before collection; it must not be changed in response to intermediate fairness results.

After every partition:

1. verify record count, duplicate count, model digest, prompt/design hashes, and three repeats;
2. generate only operational diagnostics: format yield, hallucination/off-list rate, tokens,
   elapsed time, temperature, and hardware log;
3. do not inspect trait-level fairness outcomes;
4. back up the immutable partition and its run manifest;
5. record completion in `progress.md`.

Expected complete count: **79,200 records**. Current planning estimate on a true 16 GB desktop
RTX 2000 Ada is approximately **8-12 days** of serial generation, plus engineering, audits,
analysis, interruptions, and thermal/storage overhead.

## 8. Phase G - confirmatory analysis

- [ ] Lock raw partitions read-only and create a checksummed collection manifest.
- [ ] Re-ground provider-free from immutable raw responses using the versioned matcher.
- [ ] Produce collection diagnostics and relevance controls before fairness interpretation.
- [ ] Compute user-side, item-side, utility, paired-delta, bootstrap, mixed-effects, corrected
  comparison, and RQ3 outputs separately for movies and music, then across models.
- [ ] Check convergence, residuals, singular fits, multiplicity correction, missing exposure,
  and the predeclared sensitivity analyses.
- [ ] Freeze manuscript tables and figures with an analysis-version hash. Corrections create a
  new analysis version and never mutate the frozen raw collection.

**Gate G:** reproducible tables from a clean environment, complete diagnostics, and no unresolved
analysis failure.

## 9. Phase H - mitigation and publication package

- Run RQ5 mitigation only after RQ1-RQ4 are frozen, using a separate output root and the same
  personas/candidate pools.
- Prepare the manuscript, figures, related-work verification, ethics/privacy statement,
  limitations, data/code availability statements, and journal checklist.
- Archive the lockfile, configurations, design/analysis manifests, permitted de-identified
  records, code release, and DOI.

## Immediate next action

Do **not** run the current full-collection command. It still resolves the six-persona v1 labels.
Implement Phase A and the feasibility portion of Phase B first. Only the command printed by the
final v2 preflight should be used for confirmatory collection.
