$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "== Persona Guard Test ==" -ForegroundColor Cyan

$script = @"
from aiagent.persona.persona_guard import PersonaGuard

guard = PersonaGuard()

samples = [
    "作为AI语言模型，我不能拥有真实情感。",
    "以下是解决方法：先打开设置，然后选择对应选项。",
    "番茄炒蛋一般先炒蛋，再炒番茄，最后混合翻炒。",
]

for item in samples:
    result = guard.normalize(item)
    print("INPUT :", item)
    print("OUTPUT:", result.text)
    print("CHANGED:", result.changed)
    print("REASONS:", result.reasons)
    print("-" * 60)
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
Write-Host "== Persona Guard Test Completed ==" -ForegroundColor Green
