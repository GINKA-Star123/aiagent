<#
.SYNOPSIS
    后端主链路一条命令验收：静态检查 -> 单测/契约/冒烟 ->（可选）运行中 API 探测。
.DESCRIPTION
    等价于 roadmap §10 的"本地一条命令跑完后端主链路测试"。
    - 默认跑：仓库卫生、配置一致性、tests/unit + tests/api + tests/smoke
    - -IncludeRag  追加检索质量基线（tests/rag）
    - -BaseUrl 指定时，追加运行中服务的只读探测
.NOTES
    用法：
        powershell -File scripts/test_all.ps1
        powershell -File scripts/test_all.ps1 -IncludeRag
        powershell -File scripts/test_all.ps1 -BaseUrl http://127.0.0.1:8000
    注意：
      1. 本文件含中文，必须保存为 UTF-8 with BOM。
      2. 路径统一用正斜杠：Windows 与 Python 都接受，且避免编辑器/工具链转义差异。
#>
[CmdletBinding()]
param(
    [string]$Python = "",
    [string]$BaseUrl = "",
    [switch]$IncludeRag,
    [switch]$ContinueOnFailure
)

$ErrorActionPreference = "Continue"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

# 直接探测解释器能否运行，比 Test-Path 更可靠：
# 某些受限环境（只读挂载/沙箱）下 PowerShell 提供程序对 .venv 的元数据访问会失败，
# 但进程仍可正常执行。
$candidates = @()
if (-not [string]::IsNullOrWhiteSpace($Python)) {
    $candidates += $Python
}
$candidates += @(
    (Join-Path $Root ".venv/Scripts/python.exe"),
    "python",
    "python3"
)

$resolvedPython = $null
foreach ($candidate in $candidates) {
    try {
        & $candidate -c "import sys" *> $null
        if ($LASTEXITCODE -eq 0) {
            $resolvedPython = $candidate
            break
        }
    }
    catch {
        continue
    }
}

if ($null -eq $resolvedPython) {
    throw "no usable python interpreter found; tried: " + ($candidates -join ', ')
}

$Python = $resolvedPython
$script:BaseUrl = $BaseUrl.TrimEnd("/")
$script:Results = New-Object System.Collections.Generic.List[object]

function Add-Result {
    param([string]$Name, [string]$Status, [string]$Detail = "")

    $script:Results.Add([pscustomobject]@{
        name   = $Name
        status = $Status
        detail = $Detail
    }) | Out-Null
}

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Block,
        [bool]$Required = $true
    )

    Write-Host ""
    Write-Host ("== " + $Name + " ==") -ForegroundColor Cyan

    try {
        & $Block
        Add-Result -Name $Name -Status "ok"
        Write-Host ("PASS: " + $Name) -ForegroundColor Green
    }
    catch {
        $message = $_.Exception.Message
        $status = if ($Required) { "failed" } else { "degraded" }

        Add-Result -Name $Name -Status $status -Detail $message
        Write-Host ("FAIL: " + $Name) -ForegroundColor Red
        Write-Host $message -ForegroundColor Red

        if ($Required -and -not $ContinueOnFailure) {
            throw
        }
    }
}

function Invoke-Python {
    param([string[]]$Arguments)

    & $Python @Arguments

    if ($LASTEXITCODE -ne 0) {
        throw ("python " + ($Arguments -join ' ') + " exited with code " + $LASTEXITCODE)
    }
}

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Path,
        [scriptblock]$Validate
    )

    Invoke-Step -Name $Name -Required $false -Block {
        $payload = Invoke-RestMethod -Method Get -Uri ($script:BaseUrl + $Path)
        & $Validate $payload
    }
}

Write-Host "AIAgent backend test suite" -ForegroundColor Cyan
Write-Host ("Python  : " + $Python)
Write-Host ("Workdir : " + $Root)

# ---- 1. 静态检查：仓库卫生与配置一致性 ----
Invoke-Step -Name "repo_hygiene" -Required $false -Block {
    Invoke-Python -Arguments @("scripts/check_repo_hygiene.py")
}

Invoke-Step -Name "config_sync" -Required $false -Block {
    Invoke-Python -Arguments @("scripts/check_config_sync.py")
}

# ---- 2. 单测 / 契约 / 冒烟 ----
Invoke-Step -Name "pytest_unit_api_smoke" -Block {
    Invoke-Python -Arguments @(
        "-m", "pytest",
        "tests/unit",
        "tests/api",
        "tests/smoke",
        "-q",
        "-p", "no:cacheprovider"
    )
}

if ($IncludeRag) {
    Invoke-Step -Name "pytest_rag_baseline" -Required $false -Block {
        Invoke-Python -Arguments @(
            "-m", "pytest",
            "tests/rag",
            "-q",
            "-p", "no:cacheprovider"
        )
    }
}

# ---- 3. 可选：运行中服务的只读探测 ----
if (-not [string]::IsNullOrWhiteSpace($script:BaseUrl)) {
    Test-Endpoint -Name "api_health" -Path "/health" -Validate {
        param($payload)
        if ([string]$payload.status -ne "ok") { throw "health status is not ok" }
    }

    Test-Endpoint -Name "api_ready" -Path "/ready" -Validate {
        param($payload)
        if ($null -ne $payload.details) { throw "/ready leaks details; it must stay redacted" }
        if ([string]$payload.purpose -ne "public") { throw "/ready purpose should be public" }
    }

    Test-Endpoint -Name "api_runtime_diagnostics" -Path "/runtime/diagnostics" -Validate {
        param($payload)
        if ([string]$payload.status -eq "failed") { throw "runtime diagnostics reports failure" }
    }

    Test-Endpoint -Name "api_knowledge_freshness" -Path "/knowledge/index/freshness" -Validate {
        param($payload)
        if ($null -eq $payload.freshness) { throw "missing freshness payload" }
    }

    Test-Endpoint -Name "api_vision_schema" -Path "/vision/schema" -Validate {
        param($payload)
        if ([string]::IsNullOrWhiteSpace([string]$payload.schema_version)) {
            throw "missing vision schema_version"
        }
    }

    Test-Endpoint -Name "api_live2d_stats" -Path "/live2d/stats" -Validate {
        param($payload)
        if ($null -eq $payload) { throw "empty live2d stats" }
    }
}

# ---- 4. 汇总 ----
Write-Host ""
Write-Host "== Summary ==" -ForegroundColor Cyan
$script:Results | Format-Table name, status, detail -AutoSize

$failed = @($script:Results | Where-Object { $_.status -eq "failed" })
$degraded = @($script:Results | Where-Object { $_.status -eq "degraded" })
$ok = @($script:Results | Where-Object { $_.status -eq "ok" })

Write-Host ("ok={0} degraded={1} failed={2}" -f $ok.Count, $degraded.Count, $failed.Count)

if ($failed.Count -gt 0) {
    exit 1
}

Write-Host "backend main chain passed." -ForegroundColor Green
exit 0
