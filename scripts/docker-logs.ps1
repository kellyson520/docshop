param(
  [int]$Tail = 200,
  [switch]$Follow
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

$argsList = @("compose", "logs", "--tail", "$Tail")
if ($Follow) { $argsList += "-f" }
$argsList += "docshop"

Write-Host "[DocShop] docker $($argsList -join ' ')" -ForegroundColor Cyan
& docker @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
