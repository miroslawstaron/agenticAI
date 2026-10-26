[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8876,
    [string]$DataDirectory = '',
    [switch]$External,
    [switch]$LocalOnly,
    [string[]]$AllowedHosts = @(),
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$studioRoot = $PSScriptRoot
$studioUrl = "http://127.0.0.1:$Port"
$remoteFile = Join-Path $studioRoot '.agenticai\remote-access.json'
if ($External -and $LocalOnly) { throw 'Choose either -External or -LocalOnly.' }
$remoteSettings = if (Test-Path -LiteralPath $remoteFile) { Get-Content -LiteralPath $remoteFile -Raw | ConvertFrom-Json } else { $null }
if ($External -and -not $remoteSettings) {
    $randomBytes = New-Object byte[] 32
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($randomBytes) } finally { $generator.Dispose() }
    $remoteSettings = [pscustomobject]@{ enabled = $true; username = 'studio'; password = [Convert]::ToBase64String($randomBytes) }
}
if ($remoteSettings -and ($External -or $LocalOnly)) {
    $remoteSettings.enabled = [bool]$External
    New-Item -ItemType Directory -Force -Path (Split-Path $remoteFile) | Out-Null
    $remoteSettings | ConvertTo-Json | Set-Content -LiteralPath $remoteFile -Encoding UTF8
}
$externalEnabled = [bool]($remoteSettings -and $remoteSettings.enabled -and -not $LocalOnly)
$listenAddress = if ($externalEnabled) { '0.0.0.0' } else { '127.0.0.1' }
if ($externalEnabled) {
    $env:AGENTICAI_REMOTE_USER = $remoteSettings.username
    $env:AGENTICAI_REMOTE_PASSWORD = $remoteSettings.password
    $addresses = @(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | Select-Object -ExpandProperty IPAddress)
    $names = @([System.Net.Dns]::GetHostName(), $env:COMPUTERNAME) + $addresses + $AllowedHosts + @($env:AGENTICAI_ALLOWED_HOSTS -split ',')
    $env:AGENTICAI_ALLOWED_HOSTS = (($names | Where-Object { $_ } | Sort-Object -Unique) -join ',')
} else {
    Remove-Item Env:AGENTICAI_REMOTE_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:AGENTICAI_REMOTE_USER -ErrorAction SilentlyContinue
}

function Test-StudioReady {
    try {
        $page = Invoke-WebRequest -Uri "$studioUrl/" -UseBasicParsing -TimeoutSec 2
        if ($page.StatusCode -ne 200 -or $page.Content -notmatch '<title>AgenticAI Studio</title>') {
            return $false
        }
        $sessionInfo = Invoke-RestMethod -Uri "$studioUrl/api/v1/session" -TimeoutSec 2
        return [bool]($sessionInfo.version -and $sessionInfo.data_dir)
    } catch {
        return $false
    }
}

if (Test-StudioReady) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    $isExternal = [bool]($listener | Where-Object { $_.LocalAddress -eq '0.0.0.0' -or $_.LocalAddress -eq '::' })
    if ($externalEnabled -ne $isExternal) {
        throw "Studio is already running with a different network binding. Restart its existing process before changing access mode."
    }
    Write-Host "AgenticAI Studio is already running at $studioUrl"
    if (-not $NoBrowser) { Start-Process $studioUrl }
    exit 0
}

$portProbe = [System.Net.Sockets.TcpClient]::new()
try {
    $portTask = $portProbe.ConnectAsync('127.0.0.1', $Port)
    if ($portTask.Wait(300) -and $portProbe.Connected) {
        throw "Port $Port is used by another application. Run Start-Studio.ps1 -Port <another-port>."
    }
} catch [System.AggregateException] {
    # Connection refused means the port is available.
} finally {
    $portProbe.Dispose()
}

$studioPython = Join-Path $studioRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $studioPython)) {
    throw "The project Python environment is missing. Follow the installation steps in README.md first."
}
if (-not $DataDirectory) {
    $previewDatabase = Join-Path $studioRoot '.build\studio-data\studio.sqlite3'
    $DataDirectory = if (Test-Path -LiteralPath $previewDatabase) {
        Join-Path $studioRoot '.build\studio-data'
    } else {
        Join-Path $env:USERPROFILE '.agenticai'
    }
}
$studioData = [System.IO.Path]::GetFullPath($DataDirectory)
$logDirectory = Join-Path $studioRoot '.build\studio-launcher'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$logStem = "studio-$Port-$(Get-Date -Format 'yyyyMMdd-HHmmss')-$PID"
$stdoutLog = Join-Path $logDirectory "$logStem.stdout.log"
$stderrLog = Join-Path $logDirectory "$logStem.stderr.log"

# Start independently of a temporary terminal, and open the browser only after
# the application is ready. Reusing the data directory preserves saved networks.
$serverProcess = Start-Process -FilePath $studioPython `
    -ArgumentList @('-m', 'agenticai', 'serve', '--host', $listenAddress, '--port', "$Port", '--data', ('"' + $studioData + '"')) `
    -WorkingDirectory $studioRoot -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru

for ($attempt = 0; $attempt -lt 40; $attempt++) {
    Start-Sleep -Milliseconds 250
    if (Test-StudioReady) {
        @{ pid = $serverProcess.Id; url = $studioUrl; data = $studioData; bind = $listenAddress; external = $externalEnabled; stdout = $stdoutLog; stderr = $stderrLog } |
            ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logDirectory "studio-$Port.json") -Encoding UTF8
        Write-Host "AgenticAI Studio is running at $studioUrl"
        Write-Host "Data: $studioData"
        if ($externalEnabled) {
            Write-Host "Remote addresses: $(($addresses | ForEach-Object { "http://${_}:$Port" }) -join ', ')"
            Write-Host "Remote login details: $remoteFile"
        }
        if (-not $NoBrowser) { Start-Process $studioUrl }
        exit 0
    }
    if ($serverProcess.HasExited) { break }
}
throw "Studio did not start. Inspect the startup log: $stderrLog"
