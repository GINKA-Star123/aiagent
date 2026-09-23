param(
    [string]$ComposeFile = "deploy/docker-compose.tencent.yml",
    [string]$Service = "api",
    [int]$Tail = 200
)

docker compose -f $ComposeFile logs -f --tail=$Tail $Service