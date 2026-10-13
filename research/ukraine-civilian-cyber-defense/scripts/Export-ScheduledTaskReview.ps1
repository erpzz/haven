#Requires -Version 5.1
<#
.SYNOPSIS
    Read-only local scheduled-task inventory for authorized Windows endpoints.
.DESCRIPTION
    Exports task names, actions, and task paths for offline triage. Does not change
    task settings, enumerate secrets, upload data, or contact external systems.
    Output CAN reveal usernames or paths. Keep local, redact before sharing.
.PARAMETER OutputPath
    Destination JSON file. The parent directory must exist.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$fullPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
$directory = Split-Path -Parent $fullPath
if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
    throw "Directory does not exist: $directory"
}
$inventory = @(
    Get-ScheduledTask | ForEach-Object {
        $task = $_
        [pscustomobject]@{
            TaskName = [string]$task.TaskName
            TaskPath = [string]$task.TaskPath
            State = [string]$task.State
            Actions = @($task.Actions | ForEach-Object {
                [pscustomobject]@{
                    Execute = [string]$_.Execute
                    Arguments = [string]$_.Arguments
                    WorkingDirectory = [string]$_.WorkingDirectory
                }
            })
        }
    }
)
$inventory | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $fullPath -Encoding UTF8
Write-Host "Exported $($inventory.Count) scheduled tasks to $fullPath (keep this file private)."
