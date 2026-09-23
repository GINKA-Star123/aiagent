param(
    [string]$CharacterId = "yzl",
    [string]$CharacterRoot = "data/live2d/characters",
    [string]$BackgroundRoot = "data/live2d/backgrounds"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "== Phase 3 Live2D Verification ==" -ForegroundColor Cyan

$script = @"
import ast
import json
from pathlib import Path

from aiagent.live2d.motion_mapper import Live2DMotionMapper
from aiagent.live2d.payload_builder import Live2DPayloadBuilder
from aiagent.live2d.registry import Live2DRegistry
from aiagent.live2d.scene_mapper import Live2DSceneMapper
from integrations.live2d.live2d_py_runtime import Live2DPyRuntime
from integrations.live2d.model_scanner import Live2DModelScanner
from integrations.live2d.renderer import HeadlessLive2DRenderer

syntax_paths = [
    "apps/api/routes/live2d.py",
    "apps/desktop_qt/chat_window.py",
    "apps/desktop_qt/live2d_view_panel.py",
    "integrations/live2d/qt_live2d_widget.py",
    "integrations/live2d/model_loader.py",
    "integrations/live2d/live2d_py_runtime.py",
    "integrations/live2d/model_session.py",
    "integrations/live2d/renderer.py",
    "integrations/live2d/model_scanner.py",
    "integrations/live2d/profile_generator.py",
]

syntax = {}
for item in syntax_paths:
    path = Path(item)
    ast.parse(path.read_text(encoding="utf-8-sig"))
    syntax[item] = "ok"

registry = Live2DRegistry(
    character_root=r"$CharacterRoot",
    background_root=r"$BackgroundRoot",
)
profile = registry.get_character(r"$CharacterId")

builder = Live2DPayloadBuilder(
    registry=registry,
    motion_mapper=Live2DMotionMapper(),
    scene_mapper=Live2DSceneMapper(),
)
payload = builder.build(
    character_id=profile.character_id,
    emotion="happy",
    expression="happy_smile",
    motion="smile_nod",
    background_id="room_default",
    metadata={"test": "phase3_live2d"},
)

runtime = Live2DPyRuntime()
renderer = HeadlessLive2DRenderer(runtime=runtime)

result = {
    "syntax": syntax,
    "registry": registry.stats(),
    "payload_preview": payload,
    "model_scan": Live2DModelScanner().scan_root(r"$CharacterRoot"),
    "runtime_status": runtime.status(),
    "runtime_prepare": runtime.prepare_model(profile.model3_json),
    "renderer_load": renderer.load(profile.model3_json),
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
Write-Host "== Phase 3 Live2D verification completed ==" -ForegroundColor Green
