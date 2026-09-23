param(
    [string]$CharacterId = "yzl",
    [string]$CharacterRoot = "data/live2d/characters",
    [string]$BackgroundRoot = "data/live2d/backgrounds"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "== Local Live2D Runtime Session Test ==" -ForegroundColor Cyan

$script = @"
import json
from aiagent.live2d.registry import Live2DRegistry
from integrations.live2d.renderer import HeadlessLive2DRenderer

registry = Live2DRegistry(
    character_root=r"$CharacterRoot",
    background_root=r"$BackgroundRoot",
)

profile = registry.get_character(r"$CharacterId")
renderer = HeadlessLive2DRenderer()

load_result = renderer.load(profile.model3_json)

payload = {
    "character": {
        "expression": "happy_smile",
        "motion_group": "TapBody",
        "motion_index": 0,
        "motion_priority": 2,
    },
    "scene": {
        "background_id": "room_default",
    },
    "metadata": {
        "test": "local_runtime_session",
    },
}

if load_result.get("ok"):
    apply_result = renderer.apply_payload(payload)
else:
    apply_result = {
        "ok": False,
        "stage": "skip_apply_payload",
        "reason": "model_not_loaded",
    }

result = {
    "character_id": profile.character_id,
    "model3_json": profile.model3_json,
    "load_result": load_result,
    "apply_result": apply_result,
    "snapshot": renderer.snapshot(),
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
Write-Host "== Local Live2D runtime session test completed ==" -ForegroundColor Green
