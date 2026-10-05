[CmdletBinding()]
param([ValidateSet('Enable','Disable')][string]$Action='Enable')
$ErrorActionPreference='Stop'

$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($identity)
if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
    $quoted='"'+$PSCommandPath.Replace('"','""')+'"'
    $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$quoted,'-Action',$Action)
    $p=Start-Process powershell.exe -Verb RunAs -Wait -PassThru -ArgumentList $args
    exit $p.ExitCode
}

$ruleName='Haven Model Lab LAN'
$python=Join-Path $PSScriptRoot '.local\python\python.exe'
$existing=Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

if($Action -eq 'Enable'){
    if(-not(Test-Path -LiteralPath $python)){throw 'Complete Model Lab SETUP first; the folder-local Python runtime is missing.'}
    if($existing){$existing|Remove-NetFirewallRule}
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8787 -Program $python -Profile Private -RemoteAddress LocalSubnet | Out-Null
    Write-Host 'Enabled TCP 8787 only for the Private firewall profile, LocalSubnet, and this lab Python executable.'
}else{
    if($existing){$existing|Remove-NetFirewallRule;Write-Host 'Removed the Haven Model Lab LAN firewall rule.'}
    else{Write-Host 'No Haven Model Lab LAN firewall rule was present.'}
}
