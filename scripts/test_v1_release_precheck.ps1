# scripts/test_v1_release_precheck.ps1
param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [switch]$IncludeRag,
    [switch]$IncludeRunningApiSmoke,
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AdminToken = "",
    [switch]$ContinueOnFailure,
    [switch]$AllowMissingRealEnv,
    [switch]$AllowProdMock
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Invoke-ChildScript {
    param(
        [string]$Name,
        [string]$Path,
        [string[]]$Arguments
    )

    Write-Host ""
    Write-Host "== $Name ==" -ForegroundColor Cyan

    & powershell -ExecutionPolicy Bypass -File $Path @Arguments

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$backendArgs = @("-Python", $Python)

if ($IncludeRag) {
    $backendArgs += "-IncludeRag"
}

if ($ContinueOnFailure) {
    $backendArgs += "-ContinueOnFailure"
}

if ($AllowMissingRealEnv) {
    $backendArgs += "-AllowMissingRealEnv"
}

if ($AllowProdMock) {
    $backendArgs += "-AllowProdMock"
}

Invoke-ChildScript `
    -Name "V1 backend smoke" `
    -Path "scripts\test_v1_backend_smoke.ps1" `
    -Arguments $backendArgs

if ($IncludeRunningApiSmoke) {
    $apiArgs = @("-BaseUrl", $BaseUrl)

    if (-not [string]::IsNullOrWhiteSpace($AdminToken)) {
        $apiArgs += @("-AdminToken", $AdminToken)
    }

    if ($ContinueOnFailure) {
        $apiArgs += "-ContinueOnFailure"
    }

    Invoke-ChildScript `
        -Name "V1 running API smoke" `
        -Path "scripts\test_v1_running_api_smoke.ps1" `
        -Arguments $apiArgs
}

Write-Host ""
Write-Host "== Final verification commands, not executed by this script ==" -ForegroundColor Yellow

@"
后端完整命令：
cd F:\aiagent
.\.venv\Scripts\python.exe -m pytest -q tests\unit tests\api tests\smoke -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q tests\rag -p no:cacheprovider

本地 API 启动：
cd F:\aiagent
.\.venv\Scripts\python.exe -m uvicorn apps.api.http_server:app --host 127.0.0.1 --port 8000

已启动 API smoke：
cd F:\aiagent
powershell -ExecutionPolicy Bypass -File scripts\test_v1_running_api_smoke.ps1 -BaseUrl http://127.0.0.1:8000 -AdminToken local-smoke-admin-token

云部署 compose 检查：
cd F:\aiagent
docker compose --env-file cloud.tencent.env -f deploy/docker-compose.tencent.yml config
docker compose --env-file cloud.tencent.env -f deploy/docker-compose.tencent.yml up -d --build
docker compose --env-file cloud.tencent.env -f deploy/docker-compose.tencent.yml ps

Flutter 最终验证：
cd F:\aiagent\apps\flutter_client
dart format lib test
flutter analyze
flutter test
flutter build apk --release
"@

Write-Host ""
Write-Host "V1.0.1 release precheck completed." -ForegroundColor Green