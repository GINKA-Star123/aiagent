param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "== Live2D Stats ==" -ForegroundColor Cyan

Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/live2d/stats" |
    ConvertTo-Json -Depth 50

Write-Host ""
Write-Host "== Live2D Preview: happy ==" -ForegroundColor Cyan

$happyBody = @{
    character_id = "yzl"
    emotion = "happy"
    expression = "happy_smile"
    motion = "smile_nod"
    background_id = "room_default"
    metadata = @{
        test = "happy_preview"
    }
} | ConvertTo-Json -Depth 50

Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/live2d/preview" `
    -ContentType "application/json; charset=utf-8" `
    -Body $happyBody |
    ConvertTo-Json -Depth 50

Write-Host ""
Write-Host "== Live2D Preview: vision character scene ==" -ForegroundColor Cyan

$visionBody = @{
    character_id = "yzl"
    emotion = "excited"
    image_type = "character"
    daily_scene_type = "unknown"
    topic = "music"
    metadata = @{
        test = "vision_character_scene"
    }
} | ConvertTo-Json -Depth 50

Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/live2d/preview" `
    -ContentType "application/json; charset=utf-8" `
    -Body $visionBody |
    ConvertTo-Json -Depth 50

Write-Host ""
Write-Host "== Live2D Preview: daily food scene ==" -ForegroundColor Cyan

$foodBody = @{
    character_id = "yzl"
    emotion = "calm"
    daily_scene_type = "food"
    metadata = @{
        test = "food_scene"
    }
} | ConvertTo-Json -Depth 50

Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/live2d/preview" `
    -ContentType "application/json; charset=utf-8" `
    -Body $foodBody |
    ConvertTo-Json -Depth 50

Write-Host ""
Write-Host "== Live2D Python Runtime Status ==" -ForegroundColor Cyan

Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/live2d/runtime/status" |
    ConvertTo-Json -Depth 50

Write-Host ""
Write-Host "== Live2D Python Runtime Inspect: yzl ==" -ForegroundColor Cyan

$inspectBody = @{
    character_id = "yzl"
} | ConvertTo-Json -Depth 50

Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/live2d/runtime/inspect" `
    -ContentType "application/json; charset=utf-8" `
    -Body $inspectBody |
    ConvertTo-Json -Depth 80

Write-Host ""
Write-Host "== Live2D payload test completed ==" -ForegroundColor Green
