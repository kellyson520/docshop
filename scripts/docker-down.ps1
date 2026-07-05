param(
  [switch]$RemoveVolumes
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

$argsList = @("compose", "down")
if ($RemoveVolumes) {
  Write-Host "[DocShop] Warning: Docker volumes will be removed. The bind-mounted ./data directory is not removed by this command." -ForegroundColor Yellow
  $argsList += "--volumes"
}

Write-Host "[DocShop] docker $($argsList -join ' ')" -ForegroundColor Cyan
& docker @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
