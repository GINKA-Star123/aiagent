<#
.SYNOPSIS
    第 1 批：生成 V1.2 基线报告（JSON + Markdown 摘要）。
.DESCRIPTION
    自动产物写入 data/cache/reports/（属本地运行资产，不入仓）；
    docs/v1.2-scope-and-baseline.md 请人工维护，不要被本脚本覆盖。
.NOTES
    用法：powershell -File scripts/test_v1_2_baseline.ps1
    注意：本文件含中文，必须保存为 UTF-8 with BOM。
#>
[CmdletBinding()]
param(
    [string]$Python = ".venv/Scripts/python.exe",
    [string]$JsonOutput = "data/cache/reports/v1.2-baseline.json",
    [string]$Markdown = "data/cache/reports/v1.2-baseline.md"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

if (-not (Test-Path -LiteralPath $Python)) {
    $Python = "python"
}

& $Python scripts/v1_2_baseline.py --root . --output $JsonOutput --markdown $Markdown

if ($LASTEXITCODE -ne 0) {
    Write-Host "[baseline] 采集失败" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ("[baseline] JSON : " + $JsonOutput) -ForegroundColor Green
Write-Host ("[baseline] 摘要 : " + $Markdown) -ForegroundColor Green
exit 0