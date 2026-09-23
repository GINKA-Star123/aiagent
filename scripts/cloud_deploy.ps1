param(
    [string]$ComposeFile = "deploy/docker-compose.tencent.yml"
)

$ErrorActionPreference = "Stop"

Write-Host "build images"
docker compose -f $ComposeFile build

Write-Host "start services"
docker compose -f $ComposeFile up -d

Write-Host "service status"
docker compose -f $ComposeFile ps

Write-Host "tail api logs"
docker compose -f $ComposeFile logs --tail=80 api