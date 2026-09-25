<#
.SYNOPSIS
    One-click start/stop for the local backend service stack (Redis / Qdrant / Neo4j).

.DESCRIPTION
    Wraps deploy/docker-compose.services.yml, waits until every endpoint accepts TCP
    connections, then prints the .env values the backend needs.

    This file is intentionally ASCII-only: Windows PowerShell 5.1 reads UTF-8 files
    WITHOUT BOM as ANSI, which corrupts non-ASCII characters and can break the parser.
    Keep it ASCII, or re-save it as "UTF-8 with BOM" before adding non-ASCII text.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/dev_services.ps1 -Action up
    powershell -ExecutionPolicy Bypass -File scripts/dev_services.ps1 -Action up -WithReserved
    powershell -ExecutionPolicy Bypass -File scripts/dev_services.ps1 -Action status
    powershell -ExecutionPolicy Bypass -File scripts/dev_services.ps1 -Action logs
    powershell -ExecutionPolicy Bypass -File scripts/dev_services.ps1 -Action down
    powershell -ExecutionPolicy Bypass -File scripts/dev_services.ps1 -Action app
#>
#requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('up', 'down', 'status', 'logs', 'reset', 'env', 'app')]
    [string]$Action = 'up',

    [string]$ComposeFile = '',

    [switch]$WithReserved,

    [switch]$NoWait,

    [int]$TimeoutSeconds = 120,

    [string]$ApiHost = '127.0.0.1',

    [int]$ApiPort = 8000
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ComposeFile)) {
    $ComposeFile = Join-Path $ProjectRoot 'deploy/docker-compose.services.yml'
}
$EnvFile = Join-Path $ProjectRoot '.env'

$Endpoints = @(
    @{ Name = 'Redis'; Host = '127.0.0.1'; Port = 6379; Purpose = 'queue / rate limit / execution state' },
    @{ Name = 'Qdrant'; Host = '127.0.0.1'; Port = 6333; Purpose = 'long-term memory vectors' },
    @{ Name = 'Neo4j'; Host = '127.0.0.1'; Port = 7687; Purpose = 'memory graph (MEMORY_ENABLE_GRAPH=true)' }
)
if ($WithReserved) {
    $Endpoints += @{ Name = 'Postgres'; Host = '127.0.0.1'; Port = 5432; Purpose = 'reserved, not used by the app yet' }
}

function Write-Section {
    param([string]$Text)
    Write-Host ''
    Write-Host "== $Text" -ForegroundColor Cyan
}

function Test-DockerDaemon {
    try {
        docker info *> $null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Invoke-Compose {
    param([string[]]$ComposeArgs)
    $arguments = @('compose', '-f', $ComposeFile)
    if (Test-Path $EnvFile) {
        $arguments += @('--env-file', $EnvFile)
    }
    if ($WithReserved) {
        $arguments += @('--profile', 'reserved')
    }
    $arguments += $ComposeArgs
    & docker @arguments
    if ($LASTEXITCODE -ne 0) {
        throw ("docker compose {0} failed with exit code {1}" -f ($ComposeArgs -join ' '), $LASTEXITCODE)
    }
}

function Test-Port {
    param([string]$TargetHost, [int]$Port, [int]$TimeoutMilliseconds = 1200)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $pending = $client.BeginConnect($TargetHost, $Port, $null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne($TimeoutMilliseconds)) { return $false }
        $client.EndConnect($pending)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Wait-Endpoints {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    foreach ($endpoint in $Endpoints) {
        Write-Host ("waiting for {0} on {1}:{2} ..." -f $endpoint.Name, $endpoint.Host, $endpoint.Port) -NoNewline
        $ready = $false
        while (-not $ready -and (Get-Date) -lt $deadline) {
            if (Test-Port -TargetHost $endpoint.Host -Port $endpoint.Port) {
                $ready = $true
            }
            else {
                Start-Sleep -Milliseconds 800
            }
        }
        if ($ready) {
            Write-Host ' ready' -ForegroundColor Green
        }
        else {
            Write-Host ' TIMEOUT' -ForegroundColor Yellow
        }
    }
}

function Show-Endpoints {
    Write-Section 'service endpoints'
    foreach ($endpoint in $Endpoints) {
        if (Test-Port -TargetHost $endpoint.Host -Port $endpoint.Port) {
            $state = 'up  '
        }
        else {
            $state = 'down'
        }
        Write-Host ("  [{0}] {1,-8} {2}:{3}  {4}" -f $state, $endpoint.Name, $endpoint.Host, $endpoint.Port, $endpoint.Purpose)
    }
}

function Show-EnvSnippet {
    Write-Section '.env values for the local backend'
    $lines = @(
        'REDIS_URL=redis://127.0.0.1:6379/0',
        'REDIS_PREFIX=aiagent:v1',
        'EXECUTION_STATE_MODE=redis',
        'EXECUTION_STATE_FAIL_CLOSED=true',
        'QDRANT_HOST=127.0.0.1',
        'QDRANT_PORT=6333',
        'NEO4J_URL=bolt://127.0.0.1:7687',
        'NEO4J_USERNAME=neo4j',
        'NEO4J_PASSWORD=aiagent-local-dev',
        'MEMORY_ENABLE_GRAPH=false',
        'VOICE_CALL_STORE_PROVIDER=auto'
    )
    foreach ($line in $lines) {
        Write-Host "  $line"
    }
    Write-Host '  note: NEO4J_PASSWORD must match the value compose interpolates from .env'
}

function Assert-AllEndpointsUp {
    foreach ($endpoint in $Endpoints) {
        if (-not (Test-Port -TargetHost $endpoint.Host -Port $endpoint.Port)) {
            return $false
        }
    }
    return $true
}

function Start-Services {
    if (-not (Test-Path $ComposeFile)) {
        throw "compose file not found: $ComposeFile"
    }
    if (-not (Test-DockerDaemon)) {
        Write-Host 'Docker daemon is not running. Start Docker Desktop and retry.' -ForegroundColor Red
        exit 2
    }

    Write-Section 'docker compose up -d'
    Invoke-Compose @('up', '-d')

    if (-not $NoWait) {
        Write-Section 'waiting for endpoints'
        Wait-Endpoints
    }

    Show-Endpoints
    Show-EnvSnippet
}

function Start-Api {
    $python = Join-Path $ProjectRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path $python)) {
        throw "virtualenv python not found: $python"
    }
    Write-Section ("starting API on http://{0}:{1} (Ctrl+C to stop)" -f $ApiHost, $ApiPort)
    & $python -m uvicorn apps.api.http_server:app --host $ApiHost --port $ApiPort --reload
}

if ($Action -ne 'env') {
    Push-Location $ProjectRoot
}

try {
    switch ($Action) {
        'up' {
            Start-Services
        }
        'app' {
            if (-not (Assert-AllEndpointsUp)) {
                Start-Services
            }
            else {
                Show-Endpoints
            }
            Start-Api
        }
        'down' {
            if (-not (Test-DockerDaemon)) {
                Write-Host 'Docker daemon is not running. Start Docker Desktop and retry.' -ForegroundColor Red
                exit 2
            }
            Write-Section 'docker compose down'
            Invoke-Compose @('down')
        }
        'reset' {
            if (-not (Test-DockerDaemon)) {
                Write-Host 'Docker daemon is not running. Start Docker Desktop and retry.' -ForegroundColor Red
                exit 2
            }
            $answer = Read-Host 'This deletes every local service volume. Type YES to continue'
            if ($answer -ne 'YES') {
                Write-Host 'aborted'
                return
            }
            Invoke-Compose @('down', '-v')
        }
        'status' {
            if (-not (Test-DockerDaemon)) {
                Write-Host 'Docker daemon is not running. Start Docker Desktop and retry.' -ForegroundColor Red
                exit 2
            }
            Write-Section 'docker compose ps'
            Invoke-Compose @('ps')
            Show-Endpoints
        }
        'logs' {
            if (-not (Test-DockerDaemon)) {
                Write-Host 'Docker daemon is not running. Start Docker Desktop and retry.' -ForegroundColor Red
                exit 2
            }
            Invoke-Compose @('logs', '-f', '--tail', '100')
        }
        'env' {
            Show-EnvSnippet
        }
    }
}
finally {
    if ($Action -ne 'env') {
        Pop-Location
    }
}
