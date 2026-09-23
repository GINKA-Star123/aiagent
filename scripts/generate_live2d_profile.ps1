param(
    [string]$CharacterId = "yzl",
    [string]$ModelId = "yzl_v1",
    [string]$DisplayName = "乐正绫",
    [string]$Model3Json = "",
    [string]$OutputPath = "data/live2d/characters/yzl/profile.yaml",
    [switch]$Overwrite
)

$ErrorActionPreference = "Stop"

if (-not $Model3Json) {
    throw "请传入 -Model3Json，例如 data/live2d/characters/yzl/model/yzl.model3.json"
}

Write-Host ""
Write-Host "== Generate Live2D Character Profile ==" -ForegroundColor Cyan

$overwriteValue = if ($Overwrite) { "True" } else { "False" }

$script = @"
import json
from integrations.live2d.profile_generator import Live2DProfileGenerator

generator = Live2DProfileGenerator()
profile = generator.generate_character_profile(
    character_id=r"$CharacterId",
    model_id=r"$ModelId",
    display_name=r"$DisplayName",
    model3_json=r"$Model3Json",
    output_path=r"$OutputPath",
    overwrite=$overwriteValue,
)

print(json.dumps(profile, ensure_ascii=False, indent=2, default=str))
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
Write-Host "== Profile generated: $OutputPath ==" -ForegroundColor Green
