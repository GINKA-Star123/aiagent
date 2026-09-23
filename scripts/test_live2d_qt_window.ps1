$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "== Start Qt Live2D Debug Window ==" -ForegroundColor Cyan

& .\.venv\Scripts\python.exe -m apps.desktop_qt.live2d_debug_window
