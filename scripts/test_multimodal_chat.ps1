param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$ImagePath = "",
    [string]$UserId = "multimodal_test_u001",
    [string]$Username = "multimodal_user",
    [string]$Text = ""
)

$ErrorActionPreference = "Stop"
$BaseUrl = $BaseUrl.TrimEnd("/")

if ([string]::IsNullOrWhiteSpace($Text)) {
    $Text = [System.Text.Encoding]::UTF8.GetString(
        [System.Convert]::FromBase64String("6K+35L2g55yL55yL6L+Z5byg5Zu+77yM54S25ZCO5ZKM5oiR6IGK6IGK44CC")
    )
}

function Invoke-CurlMultipart {
    param(
        [string]$Url,
        [string]$ImagePath,
        [string]$UserId,
        [string]$Username,
        [string]$Text
    )

    $tmp = [System.IO.Path]::GetTempFileName()

    try {
        $args = @(
            "-s",
            "-X", "POST",
            $Url,
            "-F", "user_id=$UserId",
            "-F", "username=$Username",
            "-F", "text=$Text",
            "-o", $tmp
        )

        if (-not [string]::IsNullOrWhiteSpace($ImagePath)) {
            if (!(Test-Path -LiteralPath $ImagePath)) {
                throw "Image file not found: $ImagePath"
            }

            $resolvedPath = (Resolve-Path -LiteralPath $ImagePath).Path
            $args += @("-F", "file=@$resolvedPath")
        }

        & curl.exe @args

        if ($LASTEXITCODE -ne 0) {
            throw "curl.exe failed with exit code $LASTEXITCODE"
        }

        $bytes = [System.IO.File]::ReadAllBytes($tmp)
        if ($bytes.Length -eq 0) {
            throw "Empty response from server."
        }

        return [System.Text.Encoding]::UTF8.GetString($bytes)
    }
    finally {
        if (Test-Path -LiteralPath $tmp) {
            Remove-Item -LiteralPath $tmp -Force
        }
    }
}

Write-Host ""
Write-Host "== Multimodal Chat Test ==" -ForegroundColor Cyan

$responseText = Invoke-CurlMultipart `
    -Url "$BaseUrl/chat/multimodal" `
    -ImagePath $ImagePath `
    -UserId $UserId `
    -Username $Username `
    -Text $Text

try {
    $result = $responseText | ConvertFrom-Json
}
catch {
    Write-Host "Invalid JSON response:" -ForegroundColor Red
    Write-Host $responseText
    throw
}

$result | ConvertTo-Json -Depth 80

Write-Host ""
Write-Host "== Key Result ==" -ForegroundColor Yellow
Write-Host "ok         :" $result.ok
Write-Host "reply      :" $result.reply
Write-Host "emotion    :" $result.emotion
Write-Host "motion     :" $result.motion
Write-Host "expression :" $result.expression

Write-Host ""
Write-Host "metadata:"
$result.metadata | ConvertTo-Json -Depth 30

Write-Host ""
Write-Host "live2d:"
$result.live2d | ConvertTo-Json -Depth 30

Write-Host ""
Write-Host "== Multimodal chat test completed ==" -ForegroundColor Green
