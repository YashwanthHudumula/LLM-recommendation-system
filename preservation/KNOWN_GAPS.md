# Known preservation gaps

## Confirmatory analysis tables

The August 15 report states that 26 domain-prefixed confirmatory-analysis files were stored at:

`C:\Users\yahu25\.codex\visualizations\2026\08\03\019fc76d-e4b9-72c2-97b1-00da6f09b6c0`

That previous-account path is absent on the current workstation, and no `recllm_movie_*` or
`recllm_music_*` files were found in the current project or the current user's common artifact
locations on 2026-08-24. The live `outputs/tables/analysis` directory contains only a single
model/domain analysis slice and is not a replacement for the missing two-domain archive.

The immutable 79,200 query records and six partition verification reports remain present.
Therefore the missing derived tables can be regenerated without model calls, but regeneration
must use a new analysis version, produce analysis manifests, and be independently hash-verified.

## Executable environment

The checked-in lockfile is present, but the local `.venv` points to a Python installation that is
no longer available. The preservation inventory can be created with built-in PowerShell/.NET
functionality; scientific analysis should wait for a clean environment reconstruction and full
test run.
