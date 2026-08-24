# Six model/domain pilot tests and results

## 1. Pilot purpose and design

The six scientific pilots tested three model snapshots in two domains under
`closed-catalog-v2`. Each pilot used six independent base preferences, 11 personality framings,
and four phrasing variants: 6 x 11 x 4 = 264 unique records. There were 44 condition cells with
six records per cell. Pilot outputs were used for grounding, format, runtime, relevance-control,
resumability, and provider-free analysis validation—not confirmatory fairness inference.

All six pilots cost USD 0 because inference was local.

## 2. Consolidated results

The table below reports the original per-pilot audit unless marked as provider-free derived.

| Model/domain | Records | Grounding result | Precision@10 | NDCG@10 | Runtime | Decision |
|---|---:|---|---:|---:|---:|---|
| Qwen/movie | 264 | 250 exact-10; mean 9.9356 | 0.5784 | 0.6551 | 35.8 min | Passed |
| Qwen/music | 264 | 251 exact-10, one 11-item list; mean 9.9583 | 0.6152 | 0.6397 | 57.4 min | Passed |
| Gemma/movie | 264 | 261 exact-10; mean 9.9886 | 0.7678 | 0.7945 | 113.3 min | Passed |
| Gemma/music | 264 | Derived 264 exact-10; mean 10.0 | 0.7402 | 0.7186 | 129.1 min | Passed after provider-free re-grounding |
| Llama/movie | 264 | Effective top-10 yield 97.27%; variable 7-28 item lists | 0.5133 | 0.5733 | 26.1 min | Passed with format/list-length caveat |
| Llama/music | 264 | Derived top-10 yield 97.88%; variable 8-14 item lists | 0.5735 | 0.5924 | 30.3 min | Passed after re-grounding with format caveat |

## 3. Qwen3 8B movie

- Snapshot: `qwen3:8b@500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`.
- 264 unique query IDs and resume identities; no empty responses.
- Matched distribution: 3 lists of 8, 11 of 9, and 250 of 10.
- Every response had at least eight matched items; exact-10 rate 94.70%.
- Four conservative fuzzy-title flags all carried valid candidate codes; zero off-list titles.
- Mean Precision@10 0.5784; mean NDCG@10 0.6551.
- Runtime 35.8 minutes; 407,797 tokens.
- Analysis produced 12 tables and 120 paired bootstrap rows. User-side mixed models converged;
  item-outcome pilot models did not converge with six personas.

The consistent v3 replay improved effective top-10 exposure yield to 99.43%, leaving two
hallucination flags and zero off-list flags.

## 4. Qwen3 8B music

- Same frozen Qwen snapshot.
- 264 unique records and no empty responses.
- Stored matched distribution: 12 lists of 9, 251 of 10, and one of 11.
- Exact-10 rate 95.08%; mean matched count 9.9583.
- Twelve valid-coded duplicate-name entries were conservatively flagged (six hallucination and
  six off-list flags in the stored diagnostic).
- Mean Precision@10 0.6152; mean NDCG@10 0.6397.
- Runtime 57.4 minutes; 394,297 tokens.
- Analysis produced 12 tables and 120 paired bootstrap rows. Six RQ3 pilot correlations were
  undefined because one rank input was constant.

The v3 replay yielded 100% top-10 exposure, zero hallucinations, and zero off-list titles.

## 5. Gemma3 12B movie

- Snapshot: `gemma3:12b@f4031aab637d1ffa37b42570452ae0e4fad0314754d17ded67322e4b95836f8a`.
- 264 unique records; matched distribution 3 lists of 9 and 261 of 10.
- Exact-10 rate 98.86%; mean matched count 9.9886.
- Zero hallucinated and zero off-list titles.
- Mean Precision@10 0.7678; mean NDCG@10 0.7945.
- Runtime 113.3 minutes; 401,697 tokens.
- Analysis produced 12 tables, 120 paired bootstrap rows, and 27/27 defined RQ3 diagnostics.
  Item-outcome mixed models still had the expected six-persona convergence limitation.

The v3 replay gave 99.89% top-10 exposure with no bad-title flags.

## 6. Gemma3 12B music

- Same frozen Gemma snapshot.
- 264 unique source records.
- The stored matcher produced 82 flags involving three recurring exact LastFM names. Every
  flagged entry had a valid candidate code and exact allowed title. The defect was duplicate-name
  resolution order, not model catalog noncompliance.
- Provider-free `exact-title-allowed-first-v2` re-grounding recovered all 82 without changing raw
  records or calling the model again.
- Derived result: 264/264 lists with 10 matches; zero hallucinated and zero off-list titles.
- Mean Precision@10 0.7402; mean NDCG@10 0.7186.
- Runtime 129.1 minutes; 383,776 tokens.
- Analysis produced 12 tables and 120 paired bootstrap rows; six RQ3 correlations were undefined
  at pilot size.

The v3 replay retained 100% top-10 exposure and zero bad-title flags.

## 7. Llama 3.1 8B movie

- Snapshot: `llama3.1:8b@46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`.
- 264 unique records; no empty responses and zero off-list titles.
- Llama frequently returned the wrong list length: 65 responses below 10 and 40 above 10;
  exact-10 rate 60.23% in the original audit.
- Four valid-coded entries had model-added annotations and were conservatively flagged.
- Primary analysis truncates overlong lists to 10 and leaves short lists short. Effective top-10
  exposure yield was 97.27% in the original audit.
- Mean Precision@10 0.5133; mean NDCG@10 0.5733.
- Runtime 26.1 minutes; 337,468 tokens.
- Analysis produced 12 tables and 120 paired bootstrap rows. All 27 pilot RQ3 diagnostics were
  classified Independent, but these are structural diagnostics, not paper findings. Three
  item-outcome fits were singular.

The v3 replay yielded 97.39% top-10 exposure, one hallucination flag, and zero off-list flags.

## 8. Llama 3.1 8B music

- Same frozen Llama snapshot.
- 264 unique records and no empty responses.
- The stored title-only matcher misread many valid titles followed by annotations. Provider-free
  annotation-aware v3 grounding recovered valid exact-title prefixes without modifying source
  records.
- Derived distribution: 4 lists of 8, 48 of 9, 188 of 10, 19 of 11, 4 of 12, and 1 of 14.
- Effective top-10 exposure yield 97.88%; four hallucination and two off-list flags remained.
- Remaining flags were invalid-code/meta lines, one replacement line containing two choices, and
  truncated names, all conservatively excluded.
- Mean Precision@10 0.5735; mean NDCG@10 0.5924.
- Runtime 30.3 minutes; 326,876 tokens.
- Analysis produced 12 tables and 120 paired bootstrap rows; 21 RQ3 diagnostics were Independent
  and six undefined; three item-outcome fits were singular.

## 9. Consistent provider-free v3 replay

| Pilot | Effective top-10 exposure yield | Hallucinated | Off-list |
|---|---:|---:|---:|
| Qwen/movie | 99.43% | 2 | 0 |
| Qwen/music | 100.00% | 0 | 0 |
| Gemma/movie | 99.89% | 0 | 0 |
| Gemma/music | 100.00% | 0 | 0 |
| Llama/movie | 97.39% | 1 | 0 |
| Llama/music | 97.88% | 4 | 2 |

Decision: all six pilots passed with documented, model-specific formatting caveats. The replay
made no model calls and changed no immutable source record.

## 10. What the pilot results do and do not establish

They establish that the software, closed catalogs, grounding, relevance controls, collection,
resumability, and analysis replay work across all six model/domain pairs. They also identify
format behavior and runtime differences.

They do not establish a publishable personality-fairness effect. Six independent personas are
too few for confirmatory mixed-model and aggregate-exposure inference. Any pilot RQ3 scenarios or
mixed-model coefficients are diagnostics only and must not be treated as final findings.
