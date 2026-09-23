# scripts/test_v1_backend_smoke.ps1
param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [switch]$IncludeRag,
    [switch]$ContinueOnFailure,
    [switch]$AllowMissingRealEnv,
    [switch]$AllowProdMock
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (-not (Test-Path -LiteralPath $Python)) {
    $Python = "python"
}

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

function Invoke-Step {
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

function Invoke-PythonCommand {
    param([string[]]$Args)

    & $Python @Args

    if ($LASTEXITCODE -ne 0) {
        # $LASTEXITCODE: 会被解析成"带作用域限定符的变量名"，必须用 ${} 界定
        throw "Python command failed with exit code ${LASTEXITCODE}: $($Args -join ' ')"
    }
}

Invoke-Step -Name "v1_preflight" -Block {
    $args = @("scripts\v1_preflight.py", "--mode", "all")

    if ($AllowMissingRealEnv) {
        $args += "--allow-missing-real-env"
    }

    if ($AllowProdMock) {
        $args += "--allow-prod-mock"
    }

    Invoke-PythonCommand -Args $args
}

Invoke-Step -Name "pytest_unit_api_smoke" -Block {
    Invoke-PythonCommand -Args @(
        "-m", "pytest",
        "-q",
        "tests\unit",
        "tests\api",
        "tests\smoke",
        "-p", "no:cacheprovider"
    )
}

if ($IncludeRag) {
    Invoke-Step -Name "pytest_rag_baseline" -Block {
        Invoke-PythonCommand -Args @(
            "-m", "pytest",
            "-q",
            "tests\rag",
            "-p", "no:cacheprovider"
        )
    }
}

Write-Host ""
Write-Host "== Backend Smoke Summary ==" -ForegroundColor Cyan
$script:Results | Format-Table name, status, detail -AutoSize

$failed = @($script:Results | Where-Object { $_.status -eq "failed" })

if ($failed.Count -gt 0) {
    exit 1
}

Write-Host "All required backend checks passed." -ForegroundColor Green