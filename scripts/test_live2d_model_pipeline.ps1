param(
    [string]$CharacterId = "yzl",
    [string]$CharacterRoot = "data/live2d/characters",
    [string]$BackgroundRoot = "data/live2d/backgrounds"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "== Live2D Model Pipeline Test ==" -ForegroundColor Cyan

$script = @"
import json
from aiagent.live2d.registry import Live2DRegistry
from integrations.live2d.model_scanner import Live2DModelScanner
from integrations.live2d.live2d_py_runtime import Live2DPyRuntime

scanner = Live2DModelScanner()
scan_result = scanner.scan_root(r"$CharacterRoot")

registry = Live2DRegistry(
    character_root=r"$CharacterRoot",
    background_root=r"$BackgroundRoot",
)

profile = registry.get_character(r"$CharacterId")

runtime = Live2DPyRuntime()
runtime_result = runtime.prepare_model(profile.model3_json)

result = {
    "scan": scan_result,
    "profile": profile.model_dump(mode="json"),
    "runtime": runtime_result,
}

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
Write-Host "== Live2D model pipeline test completed ==" -ForegroundColor Green
