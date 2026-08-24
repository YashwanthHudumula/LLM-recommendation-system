[CmdletBinding()]
param(
    [string]$StudyId = "confirmatory-study-v1"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$fullRoot = Join-Path $projectRoot (
    "outputs\queries\design=persona-relevance-v2-100-a1\stage=full\" +
    "protocol=closed-catalog-v2-a1-retry"
)
$generatedRoot = Join-Path $PSScriptRoot (Join-Path "generated" $StudyId)
$archiveRoot = Join-Path $generatedRoot "archives"
New-Item -ItemType Directory -Force -Path $archiveRoot | Out-Null

if (-not (Test-Path -LiteralPath $fullRoot)) {
    throw "Confirmatory query root is missing: $fullRoot"
}

$partitions = Get-ChildItem -LiteralPath $fullRoot -Directory -Filter "model=*" | ForEach-Object {
    Get-ChildItem -LiteralPath $_.FullName -Directory -Filter "domain=*"
} | Sort-Object FullName

if ($partitions.Count -ne 6) {
    throw "Expected six confirmatory model/domain partitions; found $($partitions.Count)"
}

$rows = [System.Collections.Generic.List[object]]::new()
foreach ($partition in $partitions) {
    $model = $partition.Parent.Name.Substring("model=".Length)
    $domain = $partition.Name.Substring("domain=".Length)
    $archiveName = "$model`__$domain`__confirmatory-records.tar.zst"
    $archivePath = Join-Path $archiveRoot $archiveName
    if (Test-Path -LiteralPath $archivePath) {
        throw "Refusing to overwrite existing archive: $archivePath"
    }

    $sourceFiles = Get-ChildItem -LiteralPath $partition.FullName -Recurse -File -Force
    $sourceBytes = [int64](($sourceFiles | Measure-Object Length -Sum).Sum)
    Write-Host "Archiving $model / $domain ($($sourceFiles.Count) files)"
    & tar -c --zstd -f $archivePath -C $partition.Parent.FullName $partition.Name
    if ($LASTEXITCODE -ne 0) {
        throw "Archive creation failed for $($partition.FullName)"
    }

    $listedEntries = @(& tar -tf $archivePath)
    if ($LASTEXITCODE -ne 0) {
        throw "Archive verification listing failed: $archivePath"
    }
    $listedFiles = @($listedEntries | Where-Object { -not $_.EndsWith("/") }).Count
    if ($listedFiles -ne $sourceFiles.Count) {
        throw "Archive file-count mismatch for $archiveName`: source=$($sourceFiles.Count), archive=$listedFiles"
    }

    $archiveItem = Get-Item -LiteralPath $archivePath
    $archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $rows.Add([pscustomobject][ordered]@{
        model = $model
        domain = $domain
        source_relative_path = [System.IO.Path]::GetRelativePath($projectRoot, $partition.FullName).Replace("\", "/")
        source_file_count = $sourceFiles.Count
        source_total_bytes = $sourceBytes
        archive_file = "archives/$archiveName"
        archive_bytes = [int64]$archiveItem.Length
        archive_sha256 = $archiveHash
        archive_listed_file_count = $listedFiles
        verified = $true
        created_at_utc = [DateTime]::UtcNow.ToString("o")
    })
}

$manifestPath = Join-Path $generatedRoot "partition_archive_manifest.tsv"
$rows | Export-Csv -LiteralPath $manifestPath -Delimiter "`t" -NoTypeInformation -Encoding utf8
$manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
$summary = [ordered]@{
    schema_version = 1
    study_id = $StudyId
    archive_count = $rows.Count
    all_verified = -not ($rows.verified -contains $false)
    archive_total_bytes = [int64](($rows | Measure-Object archive_bytes -Sum).Sum)
    manifest_file = "partition_archive_manifest.tsv"
    manifest_sha256 = $manifestHash
}
$summary | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (
    Join-Path $generatedRoot "partition_archive_summary.json"
) -Encoding utf8

Write-Host "Archive manifest: $manifestPath"
Write-Host "Archive manifest SHA256: $manifestHash"
