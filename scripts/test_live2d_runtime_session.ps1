param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$CharacterId = "yzl"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "== Live2D Runtime Load Session ==" -ForegroundColor Cyan

$loadBody = @{
    character_id = $CharacterId
} | ConvertTo-Json -Depth 50

Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/live2d/runtime/load" `
    -ContentType "application/json; charset=utf-8" `
    -Body $loadBody |
    ConvertTo-Json -Depth 80

Write-Host ""
Write-Host "== Live2D Runtime Apply Payload ==" -ForegroundColor Cyan

$payloadBody = @{
    character_id = $CharacterId
    payload = @{
        character = @{
            expression = "happy_smile"
            motion_group = "TapBody"
            motion_index = 0
            motion_priority = 2
        }
        scene = @{
            background_id = "room_default"
        }
        metadata = @{
            test = "runtime_apply_payload"
        }
    }
} | ConvertTo-Json -Depth 80

Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/live2d/runtime/apply-payload" `
    -ContentType "application/json; charset=utf-8" `
    -Body $payloadBody |
    ConvertTo-Json -Depth 100

Write-Host ""
Write-Host "== Live2D runtime session test completed ==" -ForegroundColor Green
