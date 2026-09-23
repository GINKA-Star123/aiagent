param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$ImagePath = "",
    [switch]$RunAll,
    [switch]$ContinueOnFailure
)

$ErrorActionPreference = "Stop"
$BaseUrl = $BaseUrl.TrimEnd("/")

Write-Host ""
Write-Host "== Phase 4 Closure Test ==" -ForegroundColor Cyan
Write-Host "BaseUrl: $BaseUrl"

Write-Host ""
Write-Host "== 1. Runtime Diagnostics ==" -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File scripts\test_runtime_diagnostics.ps1 `
    -BaseUrl $BaseUrl

Write-Host ""
Write-Host "== 2. Unified Test ==" -ForegroundColor Cyan

$args = @(
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts\test_all.ps1",
    "-BaseUrl", $BaseUrl
)

if ($ContinueOnFailure) {
    $args += "-ContinueOnFailure"
}

if ($RunAll) {
    $args += "-RunAll"
}

if (-not [string]::IsNullOrWhiteSpace($ImagePath)) {
    $args += @("-ImagePath", $ImagePath)
}

powershell @args

Write-Host ""
Write-Host "== Phase 4 closure test completed ==" -ForegroundColor Green
