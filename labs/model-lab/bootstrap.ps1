# Folder-local runtime; no PATH, registry, driver, firewall or execution-policy persistence.
[CmdletBinding()]
param([switch]$RuntimeOnly,[switch]$AcceptDownloads)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$local = Join-Path $root '.local'
$pythonDir = Join-Path $local 'python'
$python = Join-Path $pythonDir 'python.exe'
$version = '3.13.16'
$url = 'https://www.python.org/ftp/python/3.13.16/python-3.13.16-amd64.zip'
$expected = 'bbf675bb5e763c1efbb09a3a461b259d81598a63c30c4b0d7ea11b9f063df159'

function Expand-CheckedZip([string]$Zip, [string]$Destination) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $target = [IO.Path]::GetFullPath($Destination) + [IO.Path]::DirectorySeparatorChar
    $archive = [IO.Compression.ZipFile]::OpenRead($Zip)
    try {
        [long]$sum = 0
        foreach($entry in $archive.Entries) {
            $sum += $entry.Length
            $name = $entry.FullName.Replace('/', '\')
            $full = [IO.Path]::GetFullPath((Join-Path $Destination $name))
            if($name.Contains(':') -or -not $full.StartsWith($target,[StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe archive path.' }
        }
        if($sum -gt 1GB) { throw 'Unexpected Python archive size.' }
    } finally { $archive.Dispose() }
    [IO.Compression.ZipFile]::ExtractToDirectory($Zip,$Destination)
}
if(-not [Environment]::Is64BitOperatingSystem) { throw 'This package requires 64-bit Windows.' }
New-Item -ItemType Directory -Force -Path $local | Out-Null
if(-not (Test-Path -LiteralPath $python)) {
    Write-Host ''
    Write-Host 'Haven Model Lab needs its own Python runtime. No system Python is replaced.'
    Write-Host 'Source: official python.org / Python 3.13.16, pinned SHA-256.'
    Write-Host 'This is a small runtime download, NOT a model download.'
    if(-not $AcceptDownloads -and (Read-Host 'Download and unpack Python into this folder? [y/N]') -notmatch '^(y|yes)$') { exit 1 }
    $zip = Join-Path $local 'python-3.13.16.zip'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    if(-not (Test-Path $zip) -or (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile ($zip+'.part')
        if((Get-FileHash -LiteralPath ($zip+'.part') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'Python checksum mismatch. Nothing was executed.' }
        Move-Item -LiteralPath ($zip+'.part') -Destination $zip -Force
    }
    $stage = Join-Path $local 'python.staging'
    if(Test-Path -LiteralPath $stage) { throw 'Python staging exists; inspect the retained setup before retrying. Nothing was deleted.' }
    Expand-CheckedZip -Zip $zip -Destination $stage
    if(-not (Test-Path (Join-Path $stage 'python.exe'))) { throw 'Unexpected official Python archive layout.' }
    if(Test-Path $pythonDir) { throw 'Partial Python directory exists; inspect it before retrying.' }
    Move-Item -LiteralPath $stage -Destination $pythonDir
    @{version=$version;url=$url;sha256=$expected;installed_at=(Get-Date).ToUniversalTime().ToString('o')} | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $local 'python-receipt.json')
}
# The full archive must support the app and Strata's development environment.
# Do not infer those capabilities from the presence of python.exe alone.
& $python '-E' '-s' '-c' 'import sys, ssl, venv, ensurepip, ctypes, http.client; assert sys.maxsize > 2**32; print("Runtime verified:", sys.version.split()[0], ssl.OPENSSL_VERSION)'
if($LASTEXITCODE -ne 0) { throw 'Python runtime imports/SSL/venv/ensurepip validation failed.' }
if($RuntimeOnly) { return }
Set-Location -LiteralPath $root
& $python '-E' '-s' (Join-Path $root 'server.py') '--open'
exit $LASTEXITCODE
