[CmdletBinding()]
param(
    [string]$StudyId = "confirmatory-study-v1"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$generatedRoot = Join-Path $PSScriptRoot (Join-Path "generated" $StudyId)
$archiveRoot = Join-Path $generatedRoot "archives"
New-Item -ItemType Directory -Force -Path $archiveRoot | Out-Null

$packages = @(
    [pscustomobject]@{
        Name = "restricted-source-downloads-and-wording-audit.tar.zst"
        EvidenceClass = "restricted"
        Purpose = "Original downloaded dataset archives and the restricted wording-audit workbook"
        Paths = @(
            "data/raw/ml-1m.zip",
            "data/raw/ml-25m.zip",
            "data/raw/lastfm-dataset-1K.tar.gz",
            "data/raw/lastfm-dataset-360K.tar.gz",
            "Blind Wording Audit — Form Content (Responses) (1).xlsx"
        )
    },
    [pscustomobject]@{
        Name = "controlled-study-metadata-and-derived-evidence.tar.zst"
        EvidenceClass = "controlled"
        Purpose = "Code, frozen design, audits, documentation, derived tables, and report assets"
        Paths = @(
            "AGENTS.md",
            "README.md",
            "CITATION.cff",
            "LICENSE",
            "pyproject.toml",
            "uv.lock",
            "research_proposal_recllm_item_side_fairness (1).md",
            "progress.md",
            "progress_2026-08-06.md",
            "progress_2026-08-07.md",
            "progress_2026-08-10.md",
            "progress_2026-08-13.md",
            "progress_2026-08-15.md",
            "config",
            "data/audits",
            "data/relevance_labels",
            "data/DATA_SOURCES.md",
            "docs",
            "documentation",
            "src",
            "tests",
            "outputs/tables",
            "outputs/manuscript_assets",
            "_report_work/assets",
            "_report_work/build_final_report.py",
            "_report_work/report_v6.pdf",
            "preservation/README.md",
            "preservation/KNOWN_GAPS.md",
            "preservation/FREEZE_RECORD_2026-08-24.md"
        )
    }
)

$rows = [System.Collections.Generic.List[object]]::new()
foreach ($package in $packages) {
    $archivePath = Join-Path $archiveRoot $package.Name
    if (Test-Path -LiteralPath $archivePath) {
        throw "Refusing to overwrite existing archive: $archivePath"
    }
    foreach ($relative in $package.Paths) {
        if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $relative))) {
            throw "Supporting evidence path is missing: $relative"
        }
    }
    $sourceFiles = foreach ($relative in $package.Paths) {
        $absolute = Join-Path $projectRoot $relative
        $item = Get-Item -LiteralPath $absolute -Force
        if ($item.PSIsContainer) {
            Get-ChildItem -LiteralPath $absolute -Recurse -File -Force
        } else {
            $item
        }
    }
    $sourceFiles = @($sourceFiles | Sort-Object FullName -Unique)
    $sourceBytes = [int64](($sourceFiles | Measure-Object Length -Sum).Sum)

    Write-Host "Archiving $($package.Name) ($($sourceFiles.Count) files)"
    $tarArguments = @("-c", "--zstd", "-f", $archivePath, "-C", $projectRoot) + $package.Paths
    & tar @tarArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Supporting archive creation failed: $($package.Name)"
    }
    $listedEntries = @(& tar -tf $archivePath)
    if ($LASTEXITCODE -ne 0) {
        throw "Supporting archive verification listing failed: $($package.Name)"
    }
    $listedFiles = @($listedEntries | Where-Object { -not $_.EndsWith("/") }).Count
    if ($listedFiles -ne $sourceFiles.Count) {
        throw "Supporting archive file-count mismatch for $($package.Name): source=$($sourceFiles.Count), archive=$listedFiles"
    }
    $archiveItem = Get-Item -LiteralPath $archivePath
    $archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $rows.Add([pscustomobject][ordered]@{
        archive_file = "archives/$($package.Name)"
        evidence_class = $package.EvidenceClass
        purpose = $package.Purpose
        source_file_count = $sourceFiles.Count
        source_total_bytes = $sourceBytes
        archive_bytes = [int64]$archiveItem.Length
        archive_sha256 = $archiveHash
        archive_listed_file_count = $listedFiles
        verified = $true
        created_at_utc = [DateTime]::UtcNow.ToString("o")
    })
}

$manifestPath = Join-Path $generatedRoot "supporting_archive_manifest.tsv"
$rows | Export-Csv -LiteralPath $manifestPath -Delimiter "`t" -NoTypeInformation -Encoding utf8
$manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
$summary = [ordered]@{
    schema_version = 1
    study_id = $StudyId
    archive_count = $rows.Count
    all_verified = -not ($rows.verified -contains $false)
    archive_total_bytes = [int64](($rows | Measure-Object archive_bytes -Sum).Sum)
    manifest_file = "supporting_archive_manifest.tsv"
    manifest_sha256 = $manifestHash
}
$summary | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (
    Join-Path $generatedRoot "supporting_archive_summary.json"
) -Encoding utf8
Write-Host "Supporting archive manifest: $manifestPath"
Write-Host "Supporting archive manifest SHA256: $manifestHash"
