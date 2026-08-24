[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DestinationRoot,
    [string]$StudyId = "confirmatory-study-v1"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$source = Join-Path $PSScriptRoot (Join-Path "generated" $StudyId)
if (-not (Test-Path -LiteralPath $source)) {
    throw "Preservation source does not exist: $source"
}

$resolvedDestinationRoot = (Resolve-Path -LiteralPath $DestinationRoot).Path
if ($resolvedDestinationRoot.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The backup destination must be outside the project directory."
}
$destination = Join-Path $resolvedDestinationRoot $StudyId
if (Test-Path -LiteralPath $destination) {
    throw "Refusing to overwrite existing backup destination: $destination"
}

$sourceBytes = [int64]((Get-ChildItem -LiteralPath $source -Recurse -File | Measure-Object Length -Sum).Sum)
$destinationDrive = Get-PSDrive -Name ([System.IO.Path]::GetPathRoot($resolvedDestinationRoot).TrimEnd("\").TrimEnd(":"))
if ($destinationDrive.Free -lt ($sourceBytes * 1.10)) {
    throw "Destination does not have enough free space for a verified backup copy."
}

Write-Host "Copying $source to $destination"
Copy-Item -LiteralPath $source -Destination $destination -Recurse

$sourceInventory = Get-Content -Raw (Join-Path $source "preservation_summary.json") | ConvertFrom-Json
$destinationInventory = Get-Content -Raw (Join-Path $destination "preservation_summary.json") | ConvertFrom-Json
$destinationInventoryHash = (
    Get-FileHash -LiteralPath (Join-Path $destination $destinationInventory.inventory_file) -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($destinationInventoryHash -ne $sourceInventory.inventory_sha256) {
    throw "Destination evidence-inventory hash does not match the source freeze."
}

$sourceArchiveSummary = Get-Content -Raw (Join-Path $source "partition_archive_summary.json") | ConvertFrom-Json
$destinationManifestPath = Join-Path $destination $sourceArchiveSummary.manifest_file
$destinationManifestHash = (
    Get-FileHash -LiteralPath $destinationManifestPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($destinationManifestHash -ne $sourceArchiveSummary.manifest_sha256) {
    throw "Destination archive-manifest hash does not match the source freeze."
}

$manifest = Import-Csv -LiteralPath $destinationManifestPath -Delimiter "`t"
$checks = foreach ($row in $manifest) {
    $archivePath = Join-Path $destination $row.archive_file
    $actual = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    [pscustomobject][ordered]@{
        archive_file = $row.archive_file
        expected_sha256 = $row.archive_sha256
        actual_sha256 = $actual
        verified = ($actual -eq $row.archive_sha256)
    }
}
if ($checks.verified -contains $false) {
    throw "At least one copied archive failed SHA-256 verification."
}

$supportingSummary = Get-Content -Raw (Join-Path $source "supporting_archive_summary.json") | ConvertFrom-Json
$supportingManifestPath = Join-Path $destination $supportingSummary.manifest_file
$supportingManifestHash = (
    Get-FileHash -LiteralPath $supportingManifestPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($supportingManifestHash -ne $supportingSummary.manifest_sha256) {
    throw "Destination supporting-archive manifest does not match the source freeze."
}
$supportingManifest = Import-Csv -LiteralPath $supportingManifestPath -Delimiter "`t"
$supportingChecks = foreach ($row in $supportingManifest) {
    $archivePath = Join-Path $destination $row.archive_file
    $actual = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    [pscustomobject][ordered]@{
        archive_file = $row.archive_file
        expected_sha256 = $row.archive_sha256
        actual_sha256 = $actual
        verified = ($actual -eq $row.archive_sha256)
    }
}
if ($supportingChecks.verified -contains $false) {
    throw "At least one copied supporting archive failed SHA-256 verification."
}

$receipt = [ordered]@{
    schema_version = 1
    study_id = $StudyId
    copied_at_utc = [DateTime]::UtcNow.ToString("o")
    source = $source
    destination = $destination
    evidence_inventory_sha256 = $destinationInventoryHash
    archive_manifest_sha256 = $destinationManifestHash
    supporting_archive_manifest_sha256 = $supportingManifestHash
    archives = $checks
    supporting_archives = $supportingChecks
    all_verified = $true
}
$receiptPath = Join-Path $destination "backup_verification_receipt.json"
$receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $receiptPath -Encoding utf8
Write-Host "Verified independent backup: $destination"
Write-Host "Receipt: $receiptPath"
