param(
    [string]$CharacterId = "yzl",
    [string]$CharacterRoot = "data/live2d/characters",
    [string]$BackgroundRoot = "data/live2d/backgrounds"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "== Local Live2D Runtime Inspect ==" -ForegroundColor Cyan

$script = @"
import json
from aiagent.live2d.registry import Live2DRegistry
from integrations.live2d.live2d_py_runtime import Live2DPyRuntime

registry = Live2DRegistry(
    character_root=r"$CharacterRoot",
    background_root=r"$BackgroundRoot",
)

profile = registry.get_character(r"$CharacterId")
runtime = Live2DPyRuntime()

result = {
    "character": profile.model_dump(mode="json"),
    "runtime": runtime.status(),
    "inspection": runtime.prepare_model(profile.model3_json),
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
Write-Host "== Local Live2D runtime inspect completed ==" -ForegroundColor Green
