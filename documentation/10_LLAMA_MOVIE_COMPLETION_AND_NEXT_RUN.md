# Llama/movie confirmatory completion and next run

**Verified:** 2026-08-07 CEST
**Design:** `persona-relevance-v2-100-a1`
**Protocol:** `closed-catalog-v2-a1-retry`
**Sequence position completed:** 3 of 6

## Completion decision

Llama/movie completed 13,200/13,200 immutable records. The manifest ended as `completed`
after one safe `KeyboardInterrupt` and one successful resume. Exhaustive verification found
zero unreadable, missing, extra, duplicate, or provenance-mismatched records. The partition is
cleared to proceed **with the model-specific list-length caveat already identified in the pilot**.

This is an operational and data-quality decision, not a confirmatory fairness result. No
trait-level fairness outcomes were inspected.

## Final verification

- 13,200 manifest IDs and Parquet files; all query IDs and experimental identities unique.
- Every one of the 11 trait/level cells contains exactly 1,200 records.
- 100% of records contain at least one grounded item.
- 9,813 records (74.3409%) contain literally exactly 10 grounded items.
- 430 records are short and 2,957 are overlong; zero records have no grounded item.
- 12,770 records (96.7424%) contain at least 10 grounded items.
- Frozen first-10 truncation gives 131,290/132,000 exposure slots, or 99.4621% effective yield.
- Condition-level effective yield ranges only from 99.225% to 99.700%.
- 92 hallucinated and 13 off-list titles among 138,225 parsed titles: 0.0760% combined.
- 2,455 records (18.5985%) used the single A1 corrective retry.
- Zero invalid selected attempts, selected/raw mismatches, candidate duplicates, matched-list
  duplicates, matches outside candidate pools, or negative-token records.
- Active collection time: 13.506 hours.
- Manifest SHA256:
  `3d6b3aedf87a71a6004277a1892c8749b6abcb3c9c389534a054c13154be4db7`.

The literal exact-10 gate is not met and must not be described as met. This does not invalidate
the partition because Llama's variable-length behavior was documented in the pilot and the
primary pipeline already truncates overlong lists to the first 10 while retaining short lists.
The effective top-10 yield and bad-title gates pass. The caveat must remain in methods,
limitations, and partition-level diagnostics.

Machine-readable verification is in
`outputs/tables/full_partition_verification_persona-relevance-v2-100-a1_ollama_llama3_1_8b_movie.json`.

## Overall checkpoint

| Sequence | Partition | Records | Status |
|---:|---|---:|---|
| 1 | Qwen/movie | 13,200 | Passed |
| 2 | Qwen/music | 13,200 | Passed |
| 3 | Llama/movie | 13,200 | Passed with registered list-length caveat |
| 4 | Llama/music | 0 | Next |
| 5 | Gemma/movie | 0 | Pending |
| 6 | Gemma/music | 0 | Pending |

Overall collection: **39,600/79,200 records (50.00%)**.

## Next run

After making and verifying an independent backup of all three completed partitions, run:

```powershell
cd "D:\LLM recommend"
uv run recllm-collect --config-override config/full_run_v2_100_a1.yaml --model ollama_llama3_1_8b --domain music --stage full
```

Do not begin confirmatory fairness analysis until all six partitions are complete and verified.
