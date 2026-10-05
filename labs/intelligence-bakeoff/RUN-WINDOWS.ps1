param(
  [ValidateSet("Validate","Thin","Hermes")]
  [string]$Mode = "Validate",
  [string]$BaseUrl = "",
  [string]$Model = "",
  [string]$Label = "",
  [string]$Provider = "",
  [ValidateRange(1,10)]
  [int]$Repetitions = 3
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Need([string]$Name, [string]$Value) {
  if ([string]::IsNullOrWhiteSpace($Value)) { throw "-$Name is required for mode $Mode." }
}

if ($Mode -eq "Validate") {
  python -m unittest discover -s tests -v
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  Write-Host "Harness validation passed."
  exit 0
}

if ($Mode -eq "Thin") {
  Need "BaseUrl" $BaseUrl
  Need "Model" $Model
  if ([string]::IsNullOrWhiteSpace($Label)) { $Label = "thin-$($Model -replace '[^A-Za-z0-9._-]','-')" }
  python .\bakeoff.py --base-url $BaseUrl --model $Model --label $Label --repetitions $Repetitions
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  python .\score.py ".\runs\$Label.jsonl"
  exit $LASTEXITCODE
}

Need "Provider" $Provider
Need "Model" $Model
if (-not (Get-Command hermes -ErrorAction SilentlyContinue)) {
  throw "Hermes is not on PATH. This script never installs it automatically."
}
if ([string]::IsNullOrWhiteSpace($Label)) { $Label = "hermes-$($Model -replace '[^A-Za-z0-9._-]','-')" }
$env:HERMES_ENABLE_PROJECT_PLUGINS = "true"
$env:HAVEN_BAKEOFF_TRACE = Join-Path $PSScriptRoot "runs\$Label-tools.jsonl"
hermes plugins doctor ".\.hermes\plugins\haven-bakeoff" --ci
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python .\hermes_adapter.py --provider $Provider --model $Model --label $Label --repetitions $Repetitions
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python .\score.py ".\runs\$Label.jsonl"
exit $LASTEXITCODE
