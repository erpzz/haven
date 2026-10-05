[CmdletBinding()]
param([ValidateSet('Enable','Disable')][string]$Action='Enable')
$ErrorActionPreference='Stop'
$ruleName='Haven Model Lab LAN'
$python=Join-Path $PSScriptRoot '.local\python\python.exe'
if($Action -eq 'Enable'){
    if(-not(Test-Path -LiteralPath $python)){throw 'Complete Model Lab SETUP first; the folder-local Python runtime is missing.'}
    $existing=Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if($existing){Write-Host 'The scoped Haven LAN firewall rule already exists.';exit 0}
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8787 -Program $python -Profile Private -RemoteAddress LocalSubnet | Out-Null
    Write-Host 'Enabled TCP 8787 only for the Private firewall profile, LocalSubnet, and this lab Python executable.'
}else{
    $existing=Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if($existing){$existing|Remove-NetFirewallRule;Write-Host 'Removed the Haven Model Lab LAN firewall rule.'}
    else{Write-Host 'No Haven Model Lab LAN firewall rule was present.'}
}
