param(
    [string]$Root = "data/live2d/characters"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "== Scan Local Live2D Models ==" -ForegroundColor Cyan

$script = @"
import json
from integrations.live2d.model_scanner import Live2DModelScanner

scanner = Live2DModelScanner()
result = scanner.scan_root(r"$Root")

print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
"@

$tempFile = New-TemporaryFile

try {
    Set-Content -LiteralPath $tempFile -Value $script -Encoding UTF8
    & .\.venv\Scripts\python.exe $tempFile
}
finally {
    Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "== Scan completed ==" -ForegroundColor Green
