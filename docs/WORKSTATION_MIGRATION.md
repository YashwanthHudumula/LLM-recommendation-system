# External-SSD workstation migration and operating procedure

**Prepared:** 2026-08-03
**Laptop source:** `E:\LLM recommend`
**Portable external-SSD target:** `F:\LLM recommend` (`YASHWANTH 2TB`, NTFS)
**Target collector:** NVIDIA RTX 2000 Ada Generation, 16 GB VRAM, 32 GB DDR5 RAM

## Recommended arrangement

After the verified initial copy, the external SSD is the single portable project-data volume.
Keep these on it:

- source code, configuration, lockfile, documentation, and Git metadata;
- `data/raw`, generated label/candidate artifacts, and immutable query records;
- analysis tables, figures, manifests, and audit files.

Keep these local to each computer:

- the `uv` executable and Python project environment;
- Ollama application files and model cache;
- NVIDIA drivers and temporary/cache files.

Do not treat the external SSD as the only backup. Git does not protect raw datasets, Parquet
query records, survey workbooks, or other ignored research outputs.

## 1. Prepare the laptop before moving the drive

1. Stop every collection or analysis process and wait for the PowerShell prompt to return.
2. From the project root, record the current state:

   ```powershell
   cd "E:\LLM recommend"
   git status --short
   uv --version
   ollama --version
   ollama list
   nvidia-smi
   ```

3. Copy the complete project into a new `F:\LLM recommend` folder. Use a non-destructive copy;
   do not use `/MIR`, `/MOVE`, or any deletion option. Exclude the machine-specific `.venv` and
   disposable caches, but retain `.git`, raw datasets, immutable outputs, and ignored audit
   inputs. The 2026-08-03 dry-run inventory was 2,466 files and 6,977,811,617 bytes.
4. Verify the copied tree before designating `F:\LLM recommend` as canonical. Keep the original
   `E:` copy until an additional independent backup has also been verified.
5. The external volume was verified on 2026-08-03 as `YASHWANTH 2TB`, NTFS, writable, with
   approximately 1.7 TB free. Do not reformat it; it contains unrelated personal files.
6. Eject the drive through Windows after all programs have released it.

Use this non-destructive copy command on the laptop:

```powershell
robocopy "E:\LLM recommend" "F:\LLM recommend" /E /COPY:DAT /DCOPY:DAT /R:2 /W:2 /XJ /MT:8 /XD "E:\LLM recommend\.venv" "E:\LLM recommend\.uv-cache" "E:\LLM recommend\.pytest_cache" "E:\LLM recommend\.mypy_cache" "E:\LLM recommend\.ruff_cache" "E:\LLM recommend\outputs\pytest-tmp"
$copyExit = $LASTEXITCODE
if ($copyExit -ge 8) { throw "Robocopy failed with exit code $copyExit" }
```

Robocopy codes 0 through 7 are not fatal; code 1 normally means files were copied. Do not add
`/MIR`, `/PURGE`, or `/MOVE`. After the copy, run the same command with `/L` added. Its summary
should show zero files needing to be copied, unless a source file changed during verification.
Also compare the lockfile hash and inspect the copied Git working tree:

```powershell
Get-FileHash "E:\LLM recommend\uv.lock"
Get-FileHash "F:\LLM recommend\uv.lock"
git -C "F:\LLM recommend" status --short
```

## 2. Prepare the RTX 2000 Ada workstation

Install or verify:

- a supported NVIDIA driver;
- Git for Windows;
- the same Ollama version used for confirmatory collection;
- `uv`;
- sufficient local disk for approximately 20 GB of the three primary Ollama models, plus
  caches. More headroom is recommended.

Use the external SSD as `F:` on both computers where possible. The configuration uses relative
dataset paths, but a consistent drive letter reduces operational mistakes.

Verify the GPU and tools:

```powershell
nvidia-smi
git --version
uv --version
ollama --version
```

Do not update Ollama, NVIDIA drivers, model tags, Python dependencies, prompts, or configuration
partway through the confirmatory collection. Record any unavoidable change in `progress.md` and
the run manifest.

## 3. Recreate Python locally instead of sharing `.venv`

Python virtual environments contain machine-specific interpreter paths. Do not use the
external drive's existing `.venv` on the second computer.

In every PowerShell session used for this project on the workstation, choose a local environment
path and then run from the external project root:

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\recllm-item-fairness-venv"
cd "F:\LLM recommend"
uv sync --frozen --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
```

Use the same `UV_PROJECT_ENVIRONMENT` assignment before later `uv run` commands on that
computer. `uv.lock` supplies the exact Python package versions. The first synchronization and
sentence-transformer use may require internet access and local cache space.

The laptop should use a different local environment path following the same pattern. The
project's ignored `.venv` folder may remain as a laptop artifact, but the workstation must not
activate it.

## 4. Install the exact Ollama model snapshots

Primary configured snapshots:

| Config key | Tag | Expected digest prefix |
|---|---|---|
| `ollama_qwen3_8b` | `qwen3:8b` | `500a1f067a9f` |
| `ollama_gemma3_12b` | `gemma3:12b` | `f4031aab637d` |
| `ollama_llama3_1_8b` | `llama3.1:8b` | `46e0c10c039e` |

First try installing the three tags on the workstation:

```powershell
ollama pull qwen3:8b
ollama pull gemma3:12b
ollama pull llama3.1:8b
ollama list
```

The IDs must match the expected digest prefixes. A tag that resolves to a different digest is a
different experimental snapshot: do not silently edit `config/models.yaml` to accept it.

If a tag has changed or internet download is restricted, copy the laptop's complete
`%USERPROFILE%\.ollama\models` directory to a temporary folder on `F:`, quit Ollama
on the workstation, and copy that snapshot into the workstation user's `.ollama\models`
directory. Keep model files machine-local during the long run when local disk permits. If local
space is unavailable, Ollama officially supports a user-level `OLLAMA_MODELS` environment
variable pointing to an external model directory; restart Ollama after setting it.

Record `ollama --version`, `ollama list`, and the full model-show/digest audit before collection.

## 5. Verify GPU execution

Start one short test and inspect the loaded processor placement:

```powershell
ollama run qwen3:8b "Reply with only: READY"
ollama ps
```

The `PROCESSOR` column should report `100% GPU` when the model fits completely in VRAM. The
project uses a 2,048-token context and concurrency 1. Keep those frozen settings for the
confirmatory run; additional parallel requests consume more context memory and are not an
automatic speed improvement.

Then run the project's compatibility and v2 preflight commands after design v2 has been
implemented. Do not start the current v1 full command.

## 6. Sharing the physical drive safely

- Only one computer may mount/write the physical SSD at a time.
- Never run two collectors against the same model/domain partition.
- Do not unplug the drive while Python, Ollama, an editor, Git, antivirus, or file indexing is
  accessing the project.
- Stop the process with `Ctrl+C`, wait for the prompt, close project programs, and safely eject.
- Collection is append-only and resumable. Restarting the exact command skips completed records,
  but a hardware move during a confirmatory partition must be documented.
- For methodological consistency, complete all confirmatory inference on the RTX 2000 Ada
  workstation. Use the laptop for code work, documentation, backups, and provider-free analysis.
- If the workstation fails mid-partition, preserve the partial files. Prefer resuming on the
  same workstation after recovery. If a hardware switch is unavoidable, record the boundary
  and run a sensitivity check rather than hiding it.

## 7. Backup schedule for the full run

After each 13,200-record model/domain partition:

1. stop the collector and verify record/duplicate counts;
2. write and checksum the partition manifest;
3. copy that completed immutable partition to independent storage;
4. verify the backup before starting the next partition;
5. update `progress.md`.

Keep at least two copies of irreplaceable outputs on different physical devices. Dataset
archives can be downloaded again; week-long model outputs and frozen audit artifacts are the
priority.

## 8. Workstation acceptance gate

The workstation is cleared only when all of the following pass:

- GPU and driver detected by `nvidia-smi`;
- exact Ollama version and all three expected model digests recorded;
- `ollama ps` confirms GPU placement during generation;
- locked dependency synchronization succeeds in a machine-local environment;
- tests, lint, and strict typing pass;
- all four raw datasets load from the external SSD;
- design-v2 preflight passes grounding, format, storage, interruption, and resume checks;
- an independent full backup exists.

After verification, open `F:\LLM recommend` as the workspace in Codex and other editors. Do not
continue editing both the `E:` and `F:` copies; that would create divergent repositories and
ambiguous scientific records.
