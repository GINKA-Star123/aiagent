# scripts/test_rag_quality_report.ps1
# Complete RAG evaluation: chunking -> index -> retrieval -> rerank -> injection -> prompt.
param(
    [ValidateSet("smoke", "core", "hard", "all")]
    [string]$Suite = "all",
    [string]$Cases = "tests\fixtures\rag_eval\cases.jsonl",
    [string]$ChunkCases = "tests\fixtures\rag_eval\chunk_cases.jsonl",
    [string]$KnowledgeDir = "data\knowledge\public",
    [string]$ReportDir = "data\cache\knowledge\reports\rag_eval_v2",
    [string]$ReportPrefix = "rag_eval",
    [string]$Python = ".venv/Scripts/python.exe",
    [double]$MinPassRate = -1,
    [double]$MinRetrievalRecall = -1,
    [double]$MinRerankRecall = -1,
    [double]$MinRerankTop1 = -1,
    [double]$MinInjectionAccuracy = -1,
    [double]$MinPromptPassRate = -1,
    [double]$MinChunkPassRate = -1,
    [switch]$Required,
    [switch]$ShowResults,
    [switch]$PrintMarkdown,
    [switch]$NoChunkAudit
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (-not (Test-Path -LiteralPath $Python)) {
    $Python = "python"
}

function Resolve-RequiredPath {
    param([string]$Path, [string]$Label)

    if (Test-Path -LiteralPath $Path) {
        return
    }

    $message = "$Label not found: $Path"
    if ($Required) {
        throw $message
    }

    Write-Host "SKIP: $message" -ForegroundColor Yellow
    Write-Host "Use -Required to make this a blocking release check." -ForegroundColor Yellow
    exit 0
}

Resolve-RequiredPath -Path $Cases -Label "RAG query cases"
if (-not $NoChunkAudit) {
    Resolve-RequiredPath -Path $ChunkCases -Label "RAG chunk cases"
}
Resolve-RequiredPath -Path $KnowledgeDir -Label "RAG knowledge directory"

$Arguments = @(
    "-m", "aiagent.knowledge.evaluation.cli",
    "--suite", $Suite,
    "--cases", $Cases,
    "--chunk-cases", $ChunkCases,
    "--knowledge-dir", $KnowledgeDir,
    "--report-dir", $ReportDir,
    "--report-prefix", $ReportPrefix,
    "--write-report",
    "--show-category-summary",
    "--min-pass-rate", [string]$MinPassRate,
    "--min-retrieval-recall", [string]$MinRetrievalRecall,
    "--min-rerank-recall", [string]$MinRerankRecall,
    "--min-rerank-top1", [string]$MinRerankTop1,
    "--min-injection-accuracy", [string]$MinInjectionAccuracy,
    "--min-prompt-pass-rate", [string]$MinPromptPassRate,
    "--min-chunk-pass-rate", [string]$MinChunkPassRate
)

if ($ShowResults) {
    $Arguments += "--show-results"
}

if ($PrintMarkdown) {
    $Arguments += "--print-markdown"
}

if ($NoChunkAudit) {
    $Arguments += "--no-chunk-audit"
}

Write-Host "== RAG Evaluation ==" -ForegroundColor Cyan
Write-Host "Suite       : $Suite"
Write-Host "Cases       : $Cases"
Write-Host "ChunkCases  : $ChunkCases"
Write-Host "KnowledgeDir: $KnowledgeDir"
Write-Host "ReportDir   : $ReportDir"
Write-Host ""

& $Python @Arguments

if ($LASTEXITCODE -ne 0) {
    throw "RAG evaluation failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "RAG evaluation passed." -ForegroundColor Green
Write-Host "Report files:"
Write-Host ("- " + $ReportDir + "/" + $ReportPrefix + "_report.json")
Write-Host ("- " + $ReportDir + "/" + $ReportPrefix + "_report.md")
Write-Host ("- " + $ReportDir + "/" + $ReportPrefix + "_failures.jsonl")
