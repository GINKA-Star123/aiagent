# scripts/test_v1_running_api_smoke.ps1
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AdminToken = "",
    [switch]$ContinueOnFailure
)

$ErrorActionPreference = "Stop"
$BaseUrl = $BaseUrl.TrimEnd("/")

$script:Results = New-Object System.Collections.Generic.List[object]

function Add-Result {
    param(
        [string]$Name,
        [string]$Status,
        [string]$Detail = ""
    )

    $script:Results.Add([pscustomobject]@{
        name = $Name
        status = $Status
        detail = $Detail
    }) | Out-Null
}

function Invoke-Json {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null,
        [switch]$Admin
    )

    $headers = @{}

    if ($Admin) {
        if ([string]::IsNullOrWhiteSpace($AdminToken)) {
            throw "AdminToken is required for $Path"
        }

        $headers["x-cloud-admin-token"] = $AdminToken
    }

    $uri = "$BaseUrl$Path"

    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers
    }

    return Invoke-RestMethod `
        -Method $Method `
        -Uri $uri `
        -Headers $headers `
        -ContentType "application/json; charset=utf-8" `
        -Body ($Body | ConvertTo-Json -Depth 50)
}

function Invoke-Check {
    param(
        [string]$Name,
        [scriptblock]$Block,
        [bool]$Required = $true
    )

    Write-Host ""
    Write-Host "== $Name ==" -ForegroundColor Cyan

    try {
        & $Block
        Add-Result -Name $Name -Status "ok"
        Write-Host "PASS: $Name" -ForegroundColor Green
    }
    catch {
        $status = if ($Required) { "failed" } else { "degraded" }
        $message = $_.Exception.Message

        Add-Result -Name $Name -Status $status -Detail $message

        Write-Host "FAIL: $Name" -ForegroundColor Red
        Write-Host $message -ForegroundColor Red

        if ($Required -and -not $ContinueOnFailure) {
            throw
        }
    }
}

Invoke-Check -Name "live" -Block {
    $result = Invoke-Json -Method Get -Path "/live"
    $result | ConvertTo-Json -Depth 20
}

Invoke-Check -Name "health" -Block {
    $result = Invoke-Json -Method Get -Path "/health"
    $result | ConvertTo-Json -Depth 20

    if ($result.status -ne "ok") {
        throw "Expected health.status=ok"
    }

    if ($null -eq $result.cloud_mode) {
        throw "health response missing cloud_mode"
    }
}

Invoke-Check -Name "ready" -Block {
    $result = Invoke-Json -Method Get -Path "/ready"
    $result | ConvertTo-Json -Depth 40

    if ($null -eq $result.status) {
        throw "ready response missing status"
    }

    if ($null -eq $result.checks) {
        throw "ready response missing checks"
    }
}

Invoke-Check -Name "runtime_capabilities" -Block {
    $result = Invoke-Json -Method Get -Path "/runtime/capabilities"
    $result | ConvertTo-Json -Depth 40

    if ($result.ok -ne $true) {
        throw "runtime capabilities ok is not true"
    }

    if ($null -eq $result.capabilities) {
        throw "runtime capabilities missing capabilities"
    }
}

Invoke-Check -Name "runtime_diagnostics" -Block {
    $result = Invoke-Json -Method Get -Path "/runtime/diagnostics"
    $result | ConvertTo-Json -Depth 80

    if ($null -eq $result.status) {
        throw "runtime diagnostics missing status"
    }

    if ($null -eq $result.checks) {
        throw "runtime diagnostics missing checks"
    }
}

Invoke-Check -Name "chat" -Block {
    $result = Invoke-Json -Method Post -Path "/chat" -Body @{
        user_id = "v1-smoke-user"
        username = "V1Smoke"
        text = "你好，请用一句话回应。"
    }

    $result | ConvertTo-Json -Depth 40

    if ($result.ok -ne $true) {
        throw "chat ok is not true"
    }

    if ([string]::IsNullOrWhiteSpace([string]$result.reply)) {
        throw "chat reply is empty"
    }
}

Invoke-Check -Name "session_open" -Block {
    $result = Invoke-Json -Method Post -Path "/session/open" -Body @{
        user_id = "v1-smoke-user"
        username = "V1Smoke"
        entry = "chat_page"
        recent_topic = ""
    }

    $result | ConvertTo-Json -Depth 40

    foreach ($field in @("opening", "presence", "live2d", "memory")) {
        if ($null -eq $result.$field) {
            throw "session_open missing $field"
        }
    }
}

Invoke-Check -Name "voice_realtime_start_state_end" -Block {
    $start = Invoke-Json -Method Post -Path "/voice/realtime/start" -Body @{
        user_id = "v1-smoke-user"
        username = "V1Smoke"
    }

    $start | ConvertTo-Json -Depth 40

    if ([string]::IsNullOrWhiteSpace([string]$start.call_id)) {
        throw "voice realtime start missing call_id"
    }

    $callId = $start.call_id

    $state = Invoke-Json -Method Get -Path "/voice/realtime/state/$callId"
    $state | ConvertTo-Json -Depth 40

    if ($state.call.call_id -ne $callId) {
        throw "voice realtime state call_id mismatch"
    }

    $end = Invoke-Json -Method Post -Path "/voice/realtime/end" -Body @{
        call_id = $callId
    }

    $end | ConvertTo-Json -Depth 40

    if ($end.status -ne "ended") {
        throw "voice realtime end status is not ended"
    }
}

if (-not [string]::IsNullOrWhiteSpace($AdminToken)) {
    Invoke-Check -Name "cloud_ops_readiness" -Block {
        Invoke-Json -Method Get -Path "/cloud/ops/readiness" -Admin | ConvertTo-Json -Depth 80
    }

    Invoke-Check -Name "cloud_ops_config_snapshot" -Block {
        Invoke-Json -Method Get -Path "/cloud/ops/config-snapshot" -Admin | ConvertTo-Json -Depth 40
    }

    Invoke-Check -Name "cloud_tasks_summary" -Block {
        Invoke-Json -Method Get -Path "/cloud/tasks/summary" -Admin | ConvertTo-Json -Depth 40
    }
}
else {
    Add-Result -Name "cloud_admin_checks" -Status "degraded" -Detail "AdminToken is empty; admin checks skipped."
    Write-Host ""
    Write-Host "SKIP: cloud admin checks, AdminToken is empty." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "== Running API Smoke Summary ==" -ForegroundColor Cyan
$script:Results | Format-Table name, status, detail -AutoSize

$failed = @($script:Results | Where-Object { $_.status -eq "failed" })

if ($failed.Count -gt 0) {
    exit 1
}

Write-Host "All required running API checks passed." -ForegroundColor Green