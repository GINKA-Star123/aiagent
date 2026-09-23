<#
.SYNOPSIS
    清理本机运行产物：__pycache__ / .pytest_cache / .ruff_cache / _tmp / 前端 build。
.DESCRIPTION
    只删除被 .gitignore 忽略的产物，不触碰任何入仓文件。
    若目录带只读属性（只读挂载或沙箱遗留），先 attrib -r 再删除。
.NOTES
    用法：powershell -File scripts\clean_workspace.ps1 [-WhatIf]
    注意：本文件含中文，必须以 UTF-8 BOM 保存；
          Windows PowerShell 5.1 对无 BOM 脚本按 ANSI 代码页解析，会报语法错误。
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param()

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot

$targets = @(
    "**/__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "_tmp",
    "apps/flutter_client/build",
    "apps/flutter_client/.dart_tool"
)

function Remove-ReadOnlyDirectory {
    param([string]$Path)

    # 只读属性会让 Remove-Item 失败
    & attrib -r -s -h (Join-Path $Path '*') /s /d 2>$null | Out-Null
    Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue
}

$removed = 0
$failed = @()

foreach ($pattern in $targets) {
    $matched = Get-ChildItem -Path (Join-Path $root $pattern) -Directory -Force -ErrorAction SilentlyContinue

    foreach ($dir in $matched) {
        if ($PSCmdlet.ShouldProcess($dir.FullName, 'remove')) {
            Remove-ReadOnlyDirectory -Path $dir.FullName

            if (Test-Path -LiteralPath $dir.FullName) {
                $failed += $dir.FullName
            } else {
                $removed++
            }
        }
    }
}

Write-Host ('[clean] removed=' + $removed + ' failed=' + $failed.Count)

if ($failed.Count -gt 0) {
    Write-Host '[clean] 以下目录仍无法删除（可能被进程占用，或是只读挂载）：'
    foreach ($item in $failed) {
        Write-Host ('  - ' + $item)
    }
}
