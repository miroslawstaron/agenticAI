[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8876
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ruleName = "AgenticAI-Studio-TCP-$Port"
$displayName = "AgenticAI Studio (TCP $Port)"
$statusDirectory = Join-Path $PSScriptRoot '.build\studio-launcher'
New-Item -ItemType Directory -Force -Path $statusDirectory | Out-Null
$statusFile = Join-Path $statusDirectory "firewall-$Port.json"
try {
    $administrator = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $administrator.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Administrator approval is required to create the Studio firewall rule.'
    }
    $existing = Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
    if ($existing) {
        Set-NetFirewallRule -Name $ruleName -Enabled True -Direction Inbound -Action Allow -Profile Any | Out-Null
        $existing | Get-NetFirewallPortFilter | Set-NetFirewallPortFilter -Protocol TCP -LocalPort $Port | Out-Null
        $existing | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -LocalAddress Any -RemoteAddress Any | Out-Null
    } else {
        New-NetFirewallRule -Name $ruleName -DisplayName $displayName `
            -Description 'User-authorized remote access to AgenticAI Studio; matches the SDV and 5G HTTP rules.' `
            -Direction Inbound -Action Allow -Enabled True -Profile Any `
            -Protocol TCP -LocalPort $Port -LocalAddress Any -RemoteAddress Any | Out-Null
    }
    @{ success = $true; name = $ruleName; port = $Port } | ConvertTo-Json |
        Set-Content -LiteralPath $statusFile -Encoding UTF8
    Write-Host "Inbound TCP $Port is allowed for AgenticAI Studio."
} catch {
    @{ success = $false; name = $ruleName; port = $Port; error = $_.Exception.Message } | ConvertTo-Json |
        Set-Content -LiteralPath $statusFile -Encoding UTF8
    throw
}
