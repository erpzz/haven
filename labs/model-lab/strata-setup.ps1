# Explicit upstream installer handoff. Does not download a model until the user confirms.
[CmdletBinding()]
param([switch]$StartOnly,[ValidateSet('qwen','coder')][string]$Family='qwen')
$ErrorActionPreference = 'Stop'
$root=$PSScriptRoot
$local=Join-Path $root '.local'
$commit='6f32ec070f23ced9f50e704d854d775da52591ab'
$strata=Join-Path $local 'Strata'
$marker=Join-Path $strata 'HAVEN_SOURCE_COMMIT.txt'
if($StartOnly) {
    if(-not (Test-Path $marker) -or (Get-Content $marker -Raw).Trim() -ne $commit) { throw 'Run SETUP-STRATA.cmd first; no matching pinned installation was found.' }
    $script=if($Family -eq 'coder'){'run-coder-iq1_m.bat'}else{'run-iq2_xs.bat'}
    $path=Join-Path $strata $script
    if(-not(Test-Path $path)) { throw "The upstream setup has not produced $script. Rerun SETUP-STRATA.cmd." }
    Write-Host 'Strata runs in THIS window. Stop it with Ctrl+C/close this window.'
    Write-Host 'Do not load a second model into the 8 GB GPU at the same time.'
    Write-Host 'Connect Haven Model Lab to http://127.0.0.1:8080/v1 when ready.'
    Set-Location -LiteralPath $strata
    & $env:ComSpec /d /c $script
    exit $LASTEXITCODE
}
Write-Host ''
Write-Host 'Strata large-model experiment — RTX 2070 Super / 64 GB RAM / Ryzen 3900X'
Write-Host 'Upstream says 8 GB GPUs work slowly; no speed is promised for your PC.'
Write-Host 'Expect roughly 70 GB of model download, additional preparation files, and 35-55 GB RAM use.'
Write-Host 'Keep 100 GB free here and close RAM-heavy apps. NVMe is strongly preferred.'
Write-Host 'Upstream installs its own Python packages/CUDA runtime. Build-tool prompts must NOT be accepted automatically.'
Write-Host 'This helper does NOT change drivers, the pagefile, firewall, services or scheduled tasks.'
Write-Host 'First runtime: 8K context, image input off, one request, 1 GiB VRAM reserve.'
if((Read-Host 'Proceed with the upstream Strata installation and large download? Type STRATA') -cne 'STRATA') { exit 1 }
$drive=[IO.DriveInfo]::new([IO.Path]::GetPathRoot($root))
if($drive.AvailableFreeSpace -lt 100GB) { throw 'Less than 100 GiB free. Move this entire lab to a roomy SSD first.' }
$smi=Get-Command 'nvidia-smi.exe' -ErrorAction SilentlyContinue
if(-not $smi) {
    $candidate=Join-Path $env:WINDIR 'System32\nvidia-smi.exe'
    if(Test-Path $candidate){$smi=Get-Command $candidate}
}
if(-not $smi) { throw 'NVIDIA driver tools not found. Install/update the NVIDIA driver yourself, then retry.' }
$gpuRows=& $smi.Source '--query-gpu=name,driver_version,memory.total' '--format=csv,noheader,nounits'
if($LASTEXITCODE -ne 0){throw 'NVIDIA driver query failed.'}
Write-Host ($gpuRows -join "`n")
$first=($gpuRows | Select-Object -First 1).Split(',')
$major=[int]($first[1].Trim().Split('.')[0])
if($major -lt 528){throw 'Driver too old for the optional CUDA 12 Strata path. Update it manually.'}
$cudaArgs=@()
if($major -lt 580){$cudaArgs=@('--cuda','12');Write-Host 'Using the upstream CUDA 12 path for the installed driver.'}
& (Join-Path $root 'bootstrap.ps1') -RuntimeOnly
$python=Join-Path $local 'python\python.exe'
if(-not(Test-Path $python)){throw 'The folder-local Python runtime is missing.'}
if(Test-Path $strata) {
    if(-not(Test-Path $marker) -or (Get-Content $marker -Raw).Trim() -ne $commit){throw 'An unrelated Strata folder exists; it was not changed.'}
} else {
    $zip=Join-Path $local 'strata-source.zip'
    $url="https://github.com/Niko1221/Strata/archive/$commit.zip"
    Write-Host 'Downloading pinned upstream source from GitHub...'
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $zip
    $stage=Join-Path $local 'strata-source.staging'
    if(Test-Path $stage){Remove-Item -LiteralPath $stage -Recurse -Force}
    # This function was loaded by bootstrap.ps1 only in its own script scope, so validate here.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $a=[IO.Compression.ZipFile]::OpenRead($zip)
    try {
        [long]$sum=0
        foreach($entry in $a.Entries){$sum+=$entry.Length;if($entry.FullName.Contains('..') -or $entry.FullName.Contains(':') -or $entry.FullName.StartsWith('/')){throw 'Unsafe upstream archive member.'}}
        if($sum -gt 200MB){throw 'Unexpected upstream source archive size.'}
    } finally {$a.Dispose()}
    [IO.Compression.ZipFile]::ExtractToDirectory($zip,$stage)
    $source=Join-Path $stage "Strata-$commit"
    if(-not(Test-Path (Join-Path $source 'setup.py'))){throw 'Pinned upstream archive did not contain setup.py.'}
    Move-Item -LiteralPath $source -Destination $strata
    Set-Content -Encoding ASCII -LiteralPath $marker -Value $commit
    @{source=$url;commit=$commit;download_sha256=(Get-FileHash $zip -Algorithm SHA256).Hash;at=(Get-Date).ToUniversalTime().ToString('o');note='Source commit pinned; archive hash recorded at download, not independently pre-pinned.'} | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $local 'strata-source-receipt.json')
}
Set-Location -LiteralPath $strata
$venv=Join-Path $strata '.venv\Scripts\python.exe'
if(-not(Test-Path $venv)){& $python '-m' 'venv' '.venv';if($LASTEXITCODE -ne 0){throw 'Could not create the folder-local Strata environment.'}}
$pack=if($Family -eq 'coder'){'IQ1_M'}else{'IQ2_XS'}
$argsList=@('setup.py','--family',$Family,'--model',$pack,'--context','8192','--vision','no','--host','127.0.0.1','--port','8080','--parallel','1','--vram-reserve-mib','1024','--no-browser','--no-start','--data-dir',(Join-Path $local 'Strata-data'))+$cudaArgs
Write-Host ''
Write-Host 'Running upstream setup interactively. Do not approve driver/system-build-tool installation.'
Write-Host 'Cancellation is supported by the upstream downloader; rerun this helper to resume.'
& $venv @argsList
if($LASTEXITCODE -ne 0){throw 'Upstream Strata setup did not finish. Preserve the console error; no alternate installer will be tried.'}
Write-Host ''
Write-Host 'Setup completed. Run START-STRATA.cmd, then connect from Haven Model Lab.'
