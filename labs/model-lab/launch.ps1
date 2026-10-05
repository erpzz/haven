[CmdletBinding()]
param([ValidateSet('lab','strata')][string]$Kind='lab',[switch]$Stop,[switch]$NoBrowser)
$ErrorActionPreference='Stop'
$python=Join-Path $PSScriptRoot '.local\python\python.exe'
if(-not(Test-Path -LiteralPath $python)){throw 'Complete SETUP first; the folder-local runtime is missing.'}
$entry=Join-Path $PSScriptRoot 'launcher.py'
if($Stop){
    & $python '-X' 'utf8' $entry $Kind '--stop'
    if($LASTEXITCODE -ne 0){throw 'Stop could not be confirmed. Inspect the local launcher log.'}
}else{
    $arguments='-X utf8 "'+$entry+'" '+$Kind
    if($NoBrowser){$arguments+=' --no-browser'}
    $logRoot=Join-Path $PSScriptRoot '.local'
    $errorsPath=Join-Path $logRoot "launch-$Kind-error.txt"
    $process=Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot "launch-$Kind-output.txt") -RedirectStandardError $errorsPath -PassThru
    $receiptPath=Join-Path $logRoot "launch-$Kind.json"
    $seconds=if($Kind -eq 'strata'){360}else{60}
    $deadline=[DateTime]::UtcNow.AddSeconds($seconds)
    Write-Host 'Waiting for the local application. Use the matching STOP control to cancel startup or stop it.'
    while([DateTime]::UtcNow -lt $deadline){
        $process.Refresh()
        if($process.HasExited){
            if(Test-Path -LiteralPath $errorsPath){Get-Content -LiteralPath $errorsPath -Tail 12 | Write-Host}
            throw 'Launcher exited before readiness. Nothing outside its owned process tree was stopped.'
        }
        if(Test-Path -LiteralPath $receiptPath){
            try{$receipt=Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json}catch{$receipt=$null}
            if($receipt -and $receipt.supervisor_pid -eq $process.Id -and $receipt.url){Write-Host 'Application ready. Use its matching STOP control when finished.';exit 0}
        }
        Start-Sleep -Milliseconds 250
    }
    throw 'Application has not become ready within the startup bound. Use its STOP control and inspect the local launcher log.'
}
