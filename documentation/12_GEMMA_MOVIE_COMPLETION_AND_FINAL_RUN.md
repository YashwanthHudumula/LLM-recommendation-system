# Gemma/movie completion and final collection run

Gemma/movie completed 13,200/13,200 records and passed exhaustive verification on 2026-08-13.
Four attempts are preserved: three safe `KeyboardInterrupt` pauses and one completed resume.

## Final quality

- Zero missing, extra, unreadable, duplicate, or provenance-mismatched records.
- 100% contain at least one grounded recommendation.
- 13,091 records (99.1742%) contain exactly 10 grounded items.
- Effective top-10 exposure yield: 99.9174%.
- 104 hallucinated and 5 off-list titles among 132,010 parsed titles: 0.0826% combined.
- 207 records (1.5682%) used the A1 retry.
- Every trait/level condition contains exactly 1,200 records.
- Manifest SHA256:
  `b921d6fb054d2d5c79d26662b9f4f89c7600f73ad9219b2646c5f14ab23ef249`.

The partition passes all registered operational quality gates. Confirmatory fairness outcomes
remain uninspected.

## Collection checkpoint

Five of six partitions are complete: **66,000/79,200 records (83.33%)**. Gemma/music is the
only remaining collection partition.

## Final run command

After backup and checksum verification:

```powershell
cd "D:\LLM recommend"
uv run recllm-collect --config-override config/full_run_v2_100_a1.yaml --model ollama_gemma3_12b --domain music --stage full
```

After Gemma/music finishes, audit it before running the frozen confirmatory analysis.
