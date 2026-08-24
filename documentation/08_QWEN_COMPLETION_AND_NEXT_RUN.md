# Qwen confirmatory completion and next run

**Checkpoint:** 2026-08-06
**Design:** `persona-relevance-v2-100-a1`
**Protocol:** `closed-catalog-v2-a1-retry`

## Qwen/movie final result

- 13,200/13,200 records; completed after three resumable attempts.
- 100% at-least-one-grounded yield.
- 95.4394% exact-10 yield.
- 0.6101% combined hallucination/off-list incidence.
- 1,303 retries (9.8712%).
- No structural, provenance, attempt-selection, candidate, or token defects.
- Balanced 1,200 records in every trait/level cell.
- Manifest SHA256:
  `9ff1a20a9139d5e2938818e4a86f4eac369fb72d2f763675b7355adb4543e957`.
- Verification report:
  `outputs/tables/full_partition_verification_persona-relevance-v2-100-a1_ollama_qwen3_8b_movie.json`.

## Qwen/music final result

- 13,200/13,200 records; completed after two resumable attempts.
- Active collection time 12.928 hours.
- 100% at-least-one-grounded yield.
- 99.8485% exact-10 yield.
- 2 hallucinated titles, zero off-list titles, 132,015 parsed titles.
- 0.0015% combined hallucination/off-list incidence.
- 343 retries (2.5985%).
- 19 underlength records and zero zero-grounded records.
- No structural, provenance, attempt-selection, candidate, or token defects.
- Balanced 1,200 records in every trait/level cell.
- Manifest SHA256:
  `c9dd180f2d9ada4e1761d59cd8c6f418074700f345dfefa4c428ed5bb9a894ff`.
- Verification report:
  `outputs/tables/full_partition_verification_persona-relevance-v2-100-a1_ollama_qwen3_8b_music.json`.

Both Qwen partitions passed the frozen operational gates. These are collection-quality results,
not trait-level fairness findings.

## Collection checkpoint

The project has completed **26,400/79,200 records (33.33%)**. The Qwen model is complete across
both domains. Four partitions remain.

## Next frozen run: Llama/movie

```powershell
cd "D:\LLM recommend"
uv run recllm-collect --config-override config/full_run_v2_100_a1.yaml --model ollama_llama3_1_8b --domain movie --stage full
```

Before starting, create and verify an independent backup of the two Qwen partitions, their
`run_manifest.json` files, and both final verification reports.

## Documentation ACL note

The migrated external drive retains an earlier Windows SID on pre-existing Markdown files.
Windows allowed new documentation and verification files to be created but denied replacement of
the original README/progress/documentation files. Therefore this dated file and
`README_CURRENT_2026-08-06.md` are the authoritative execution-status updates; original files are
preserved as historical snapshots.
