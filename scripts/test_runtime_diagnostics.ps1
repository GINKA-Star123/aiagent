param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "== Runtime Diagnostics ==" -ForegroundColor Cyan

try {
    $result = Invoke-RestMethod `
        -Method Get `
        -Uri "$BaseUrl/runtime/diagnostics"

    $result | ConvertTo-Json -Depth 80

    Write-Host ""
    Write-Host "== Summary ==" -ForegroundColor Cyan
    Write-Host "ok       : $($result.ok)"
    Write-Host "status   : $($result.status)"
    Write-Host "ok       : $($result.summary.ok)"
    Write-Host "degraded : $($result.summary.degraded)"
    Write-Host "failed   : $($result.summary.failed)"
    Write-Host "skipped  : $($result.summary.skipped)"

    Write-Host ""
    Write-Host "== Non-OK Checks ==" -ForegroundColor Yellow

    $nonOk = @($result.checks | Where-Object { $_.status -ne "ok" })

    if ($nonOk.Count -eq 0) {
        Write-Host "All checks are ok." -ForegroundColor Green
    }
    else {
        $nonOk |
            Select-Object name, status, summary, action |
            Format-Table -AutoSize
    }
}
catch {
    Write-Host ""
    Write-Host "Runtime diagnostics request failed." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    throw
}
