# Documentation update manifest — 2026-08-06

## Authoritative status updates

| File | Purpose | SHA256 |
|---|---|---|
| `../README_CURRENT_2026-08-06.md` | Current project README and next command | `67dffbe419d2c3c1c9e3228ec51ffd4c43df50ff2bb02e5e0c812ae33684103a` |
| `../progress_2026-08-06.md` | Current completion checkpoint | `d6529a6061a682aacd336c861961a0f5f8825c1c772114e6faf066c10e6ba446` |
| `08_QWEN_COMPLETION_AND_NEXT_RUN.md` | Final Qwen results and next partition | `46ba1dc8f6148db71bfad9e16fb9fc3b165319a51a5e490fd35fa1f580d986cb` |

## Final machine-readable verification

| File | SHA256 |
|---|---|
| `../outputs/tables/full_partition_verification_persona-relevance-v2-100-a1_ollama_qwen3_8b_music.json` | `3cfef096f48197b640928153ace5148eae7f2cda7b6e1302357c258aa885bf56` |

The verification JSON reports `passed`, 13,200 records, 100% at-least-one-grounded yield,
99.8485% exact-10 yield, and 0.0015% combined hallucination/off-list incidence.

## ACL disposition

Pre-existing Markdown files on the migrated external drive could be read but not replaced because
Windows retained the earlier workstation/user ownership. Permission was narrowed to documentation
files only, but Windows continued to deny replacement of the original files. No broader drive
ownership or source/data permissions were changed.

The dated files above therefore supersede stale execution-status sections while preserving the
original documentation as historical evidence. Methodology, architecture, six-pilot results,
frozen configurations, and audit source mappings in the original documentation set remain valid.
