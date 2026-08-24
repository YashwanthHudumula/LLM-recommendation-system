# Llama/music confirmatory completion and next run

**Verified:** 2026-08-10 CEST
**Design:** `persona-relevance-v2-100-a1`
**Protocol:** `closed-catalog-v2-a1-retry`
**Sequence position completed:** 4 of 6

## Decision

Llama/music completed 13,200/13,200 immutable records after one safe pause and one successful
resume. Exhaustive verification found no missing, extra, unreadable, duplicate, structurally
invalid, or provenance-mismatched records. It passes with the registered Llama variable-list-
length caveat. No confirmatory fairness outcomes were inspected.

## Final quality

- 100% of records contain grounded recommendations; zero are empty.
- Literal exact-10: 10,600 records (80.3030%).
- Short: 149 records; overlong: 2,451 records.
- At least 10 grounded: 98.8712%.
- Frozen first-10 effective exposure yield: 131,815/132,000 slots (99.8598%).
- Condition-level effective yield range: 99.6833% to 99.9333%.
- 39 hallucinated and 11 off-list titles among 135,438 parsed titles (0.0369%).
- 1,233 records used the A1 retry (9.3409%).
- Every trait/level cell contains exactly 1,200 records.
- Active collection time: 11.936 hours.
- Manifest SHA256:
  `8a4608bed57f64d2edca97becb4ba2553511e8c3a52c8761387a7bd99b36c118`.

Literal exact-10 does not meet the generic 90% threshold and must remain a reported limitation.
The effective top-10 and bad-title gates pass under the frozen Llama handling established before
confirmatory analysis.

## Overall checkpoint

| Sequence | Partition | Records | Status |
|---:|---|---:|---|
| 1 | Qwen/movie | 13,200 | Passed |
| 2 | Qwen/music | 13,200 | Passed |
| 3 | Llama/movie | 13,200 | Passed with registered length caveat |
| 4 | Llama/music | 13,200 | Passed with registered length caveat |
| 5 | Gemma/movie | 0 | Next |
| 6 | Gemma/music | 0 | Pending |

Overall collection: **52,800/79,200 records (66.67%)**.

## Next command

After independent backup and checksum verification:

```powershell
cd "D:\LLM recommend"
uv run recllm-collect --config-override config/full_run_v2_100_a1.yaml --model ollama_gemma3_12b --domain movie --stage full
```
