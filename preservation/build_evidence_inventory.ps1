[CmdletBinding()]
param(
    [string]$StudyId = "confirmatory-study-v1",
    [int]$Workers = 16
)

$ErrorActionPreference = "Stop"
$python = (Get-Command python -ErrorAction Stop).Source
& $python (Join-Path $PSScriptRoot "build_evidence_inventory.py") `
    --study-id $StudyId `
    --workers $Workers
if ($LASTEXITCODE -ne 0) {
    throw "Evidence inventory failed with exit code $LASTEXITCODE"
}
