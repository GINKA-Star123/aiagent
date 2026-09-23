param(
    [string]$ComposeFile = "deploy/docker-compose.tencent.yml",
    [string]$BackupDir = "data/backups",
    [string]$Timestamp = ""
)

$ErrorActionPreference = "Stop"

if (-not $Timestamp) {
    $Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
}

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$PostgresBackup = Join-Path $BackupDir "postgres-$Timestamp.sql"
$QdrantBackup = Join-Path $BackupDir "qdrant-storage-$Timestamp.tar"
$DataBackup = Join-Path $BackupDir "data-$Timestamp.tar"

Write-Host "backup postgres -> $PostgresBackup"
docker compose -f $ComposeFile exec -T postgres pg_dump -U aiagent aiagent | Out-File -Encoding utf8 $PostgresBackup

Write-Host "backup qdrant volume -> $QdrantBackup"
docker run --rm `
    -v aiagent_qdrant_data:/volume `
    -v "${PWD}/${BackupDir}:/backup" `
    alpine `
    tar -cf "/backup/qdrant-storage-$Timestamp.tar" -C /volume .

Write-Host "backup data volume -> $DataBackup"
docker run --rm `
    -v aiagent_aiagent_data:/volume `
    -v "${PWD}/${BackupDir}:/backup" `
    alpine `
    tar -cf "/backup/data-$Timestamp.tar" -C /volume .

Write-Host "backup completed"