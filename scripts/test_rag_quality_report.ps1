# scripts/test_rag_quality_report.ps1
param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$Cases = "tests\fixtures\rag_eval\cases.jsonl",
    [string]$KnowledgeDir = "data\knowledge\public",
    [string]$ReportDir = "data\cache\knowledge\reports",
    [string]$ReportPrefix = "rag_eval",
    [double]$MinPassRate = 0.75,
    [double]$MinRecallAt1 = 0.40,
    [double]$MinRecallAt3 = 0.80,
    [double]$MinMrr = 0.55,
    [switch]$Required,
    [switch]$ShowResults,
    [switch]$PrintMarkdown
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (-not (Test-Path -LiteralPath $Python)) {
    $Python = "python"
}

if (-not (Test-Path -LiteralPath $Cases)) {
    throw "RAG eval cases file not found: $Cases"
}

if (-not (Test-Path -LiteralPath $KnowledgeDir)) {
    $message = "RAG knowledge directory not found: $KnowledgeDir"

    if ($Required) {
        throw $message
    }

    Write-Host "SKIP: $message" -ForegroundColor Yellow
    Write-Host "Use -Required to make this a blocking release check." -ForegroundColor Yellow
    exit 0
}

$args = @(
    "-m", "aiagent.knowledge.rag_eval",
    "--cases", $Cases,
    "--knowledge-dir", $KnowledgeDir,
    "--min-pass-rate", [string]$MinPassRate,
    "--min-recall-at-1", [string]$MinRecallAt1,
    "--min-recall-at-3", [string]$MinRecallAt3,
    "--min-mrr", [string]$MinMrr,
    "--show-category-summary",
    "--write-report",
    "--report-dir", $ReportDir,
    "--report-prefix", $ReportPrefix
)

if ($ShowResults) {
    $args += "--show-results"
}

if ($PrintMarkdown) {
    $args += "--print-markdown"
}

Write-Host "== RAG Quality Report ==" -ForegroundColor Cyan
Write-Host "Cases       : $Cases"
Write-Host "KnowledgeDir: $KnowledgeDir"
Write-Host "ReportDir   : $ReportDir"
Write-Host ""

& $Python @args

if ($LASTEXITCODE -ne 0) {
    throw "RAG quality report failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "RAG quality report passed." -ForegroundColor Green
Write-Host "Report files:"
Write-Host "- $ReportDir\$ReportPrefix`_report.json"
Write-Host "- $ReportDir\$ReportPrefix`_report.md"
Write-Host "- $ReportDir\$ReportPrefix`_failures.jsonl"