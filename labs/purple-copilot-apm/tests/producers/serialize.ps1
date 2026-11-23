# Pinned source files are downloaded separately to SourceDir. Never load a tenant module.
param([string]$SourceDir, [string]$OutputDir)
$ErrorActionPreference = 'Stop'
$tenant = '6c12b0b0-b2cc-4a73-8252-0b94bfca2145'
$fixture = Join-Path $PSScriptRoot '../offline_fixtures/entraops_eam.json'
New-Item "$OutputDir/EntraID" -ItemType Directory -Force | Out-Null
Copy-Item $fixture "$OutputDir/EntraID/EntraID.json"
. "$SourceDir/eo.ps1"
Export-EntraOpsPrivilegedEAMBloodHound -ImportPath $OutputDir -TenantId $tenant -RbacSystems EntraID -OutputPath "$OutputDir/opengraph.json" | Out-Null
# Replace only external session and catalog dependencies of the stable report writer.
function Test-MtConnection($service) { return $service -eq 'Graph' }
function Get-MgContext { return [pscustomobject]@{TenantId=$tenant; Account='synthetic'} }
function Invoke-MtGraphRequest { return [pscustomobject]@{DisplayName='synthetic'} }
function Get-MtModuleVersion { return [version]'2.3.0' }
function Get-MtMaesterConfigTestSetting { return $null }
$__MtSession = @{TestResultDetail=@{}}
$test = [pscustomobject]@{ ExpandedName='MT.SYN.824: Synthetic configuration'; Name='MT.SYN.824'; Result='Passed'; ScriptBlock={}; Block=@{Tag=@()}; Tag=@(); Duration=[timespan]::Zero }
$pester = [pscustomobject]@{Tests=@($test); Containers=@(); ExecutedAt=[datetime]'2026-11-21T19:00:00Z'; Result='Passed'; Duration=[timespan]::Zero; UserDuration=[timespan]::Zero; DiscoveryDuration=[timespan]::Zero; FrameworkDuration=[timespan]::Zero}
. "$SourceDir/stable.ps1"
$report = ConvertTo-MtMaesterResult -PesterResults $pester -SkipVersionCheck
$report | ConvertTo-Json -Depth 20 | Set-Content "$OutputDir/maester.json"
