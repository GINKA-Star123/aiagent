param(
    [string]$BaseUrl = "http://127.0.0.1",
    [int]$Concurrency = 100,
    [int]$Total = 300
)

$ErrorActionPreference = "Stop"

$ScriptBlock = {
    param($BaseUrl, $Index)

    $Body = @{
        user_id = "load-$($Index % 20)"
        username = "load"
        text = "并发压测消息 $Index"
    } | ConvertTo-Json

    try {
        $Started = Get-Date
        $Response = Invoke-WebRequest `
            -Method POST `
            -Uri "$BaseUrl/chat" `
            -ContentType "application/json" `
            -Body $Body `
            -TimeoutSec 90

        $Elapsed = ((Get-Date) - $Started).TotalMilliseconds

        [pscustomobject]@{
            index = $Index
            status = [int]$Response.StatusCode
            ms = [int]$Elapsed
            ok = $true
        }
    }
    catch {
        [pscustomobject]@{
            index = $Index
            status = 0
            ms = 0
            ok = $false
            error = $_.Exception.Message
        }
    }
}

$Jobs = @()
for ($i = 1; $i -le $Total; $i++) {
    while (($Jobs | Where-Object { $_.State -eq "Running" }).Count -ge $Concurrency) {
        Start-Sleep -Milliseconds 100
        $Done = $Jobs | Where-Object { $_.State -ne "Running" }
        foreach ($Job in $Done) {
            Receive-Job $Job
            Remove-Job $Job
            $Jobs = $Jobs | Where-Object { $_.Id -ne $Job.Id }
        }
    }

    $Jobs += Start-Job -ScriptBlock $ScriptBlock -ArgumentList $BaseUrl, $i
}

while ($Jobs.Count -gt 0) {
    Start-Sleep -Milliseconds 100
    $Done = $Jobs | Where-Object { $_.State -ne "Running" }
    foreach ($Job in $Done) {
        Receive-Job $Job
        Remove-Job $Job
        $Jobs = $Jobs | Where-Object { $_.Id -ne $Job.Id }
    }
}