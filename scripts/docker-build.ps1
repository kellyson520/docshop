param(
  [switch]$NoCache,
  [switch]$Pull,
  [switch]$Up,
  [string]$Service = "docdist"
)

$ErrorActionPreference = "Stop"

$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"

$buildArgs = @("compose", "build")
if ($Pull) { $buildArgs += "--pull" }
if ($NoCache) { $buildArgs += "--no-cache" }
$buildArgs += $Service

Write-Host "[DocDist] BuildKit enabled" -ForegroundColor Cyan
Write-Host "[DocDist] docker $($buildArgs -join ' ')" -ForegroundColor Cyan
& docker @buildArgs

if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

if ($Up) {
  Write-Host "[DocDist] Starting service: $Service" -ForegroundColor Cyan
  & docker compose up -d $Service
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}
