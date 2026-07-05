param(
  [switch]$NoCache,
  [switch]$Pull,
  [switch]$Up,
  [string]$Service = "docshop",
  [string]$Port = "8080",
  [string]$BaseMirror = $env:DOCKER_BASE_MIRROR
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"
if (-not $env:DOCSHOP_PORT) { $env:DOCSHOP_PORT = $Port }
if (-not $env:PIP_INDEX_URL) { $env:PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple" }
if (-not $env:PIP_TRUSTED_HOST) { $env:PIP_TRUSTED_HOST = "pypi.tuna.tsinghua.edu.cn" }

$defaultNodeImage = "node:18.20.8-alpine3.20"
$defaultPythonImage = "python:3.11.11-slim-bookworm"
$defaultBaseMirrors = @(
  "docker.m.daocloud.io/library",
  "registry.cn-hangzhou.aliyuncs.com/library"
)
$defaultMirrorTimeoutSeconds = 2

function Get-DotEnvValue {
  param([string]$Name)
  if (-not (Test-Path ".env")) { return "" }
  $pattern = "^\s*$([regex]::Escape($Name))\s*="
  $line = Get-Content ".env" | Where-Object { $_ -match $pattern } | Select-Object -First 1
  if (-not $line) { return "" }
  return (($line -replace "^\s*[^=]+\s*=", "").Trim().Trim('"').Trim("'"))
}

function Test-DockerHubReachable {
  try {
    $response = Invoke-WebRequest -Uri "https://registry-1.docker.io/v2/" -Method Head -TimeoutSec 3 -UseBasicParsing
    return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
  } catch {
    $response = $_.Exception.Response
    if ($response -and [int]$response.StatusCode -lt 500) {
      return $true
    }
    return $false
  }
}

function Normalize-DockerMirrorPrefix {
  param([string]$Mirror)
  if ([string]::IsNullOrWhiteSpace($Mirror)) { return "" }
  $prefix = $Mirror.Trim().TrimEnd("/")
  $prefix = $prefix -replace "^https?://", ""
  if ($prefix.ToLowerInvariant() -eq "off") { return "" }
  return $prefix
}

function Get-DockerRegistryProbeUrl {
  param([string]$Mirror)
  $prefix = Normalize-DockerMirrorPrefix $Mirror
  if ([string]::IsNullOrWhiteSpace($prefix)) { return "https://registry-1.docker.io/v2/" }
  $host = ($prefix -split "/")[0]
  return "https://$host/v2/"
}

function Measure-DockerRegistryLatency {
  param(
    [string]$Mirror,
    [int]$TimeoutSeconds
  )
  $uri = Get-DockerRegistryProbeUrl $Mirror
  $watch = [System.Diagnostics.Stopwatch]::StartNew()
  try {
    $response = Invoke-WebRequest -Uri $uri -Method Head -TimeoutSec $TimeoutSeconds -UseBasicParsing
    $watch.Stop()
    if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) { return $watch.ElapsedMilliseconds }
  } catch {
    $watch.Stop()
    $response = $_.Exception.Response
    if ($response -and [int]$response.StatusCode -lt 500) { return $watch.ElapsedMilliseconds }
  }
  return [int]::MaxValue
}

function Get-DockerMirrorCandidates {
  $raw = $env:DOCKER_MIRROR_CANDIDATES
  if ([string]::IsNullOrWhiteSpace($raw)) { $raw = Get-DotEnvValue "DOCKER_MIRROR_CANDIDATES" }
  if ([string]::IsNullOrWhiteSpace($raw)) { return $defaultBaseMirrors }
  $items = @($raw -split "," | ForEach-Object { Normalize-DockerMirrorPrefix $_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
  if ($items.Count -eq 0) { return $defaultBaseMirrors }
  return $items
}

function Get-DockerMirrorTimeoutSeconds {
  $raw = $env:DOCKER_MIRROR_TIMEOUT_SECONDS
  if ([string]::IsNullOrWhiteSpace($raw)) { $raw = Get-DotEnvValue "DOCKER_MIRROR_TIMEOUT_SECONDS" }
  $value = 0
  if ([int]::TryParse($raw, [ref]$value) -and $value -ge 1) { return $value }
  return $defaultMirrorTimeoutSeconds
}

function Select-FastestDockerMirror {
  $candidates = @(Get-DockerMirrorCandidates)
  $timeoutSeconds = Get-DockerMirrorTimeoutSeconds
  $bestMirror = ""
  $bestMs = [int]::MaxValue

  foreach ($candidate in $candidates) {
    $latencyMs = Measure-DockerRegistryLatency $candidate $timeoutSeconds
    if ($latencyMs -lt $bestMs) {
      $bestMs = $latencyMs
      $bestMirror = $candidate
    }
  }

  if (-not [string]::IsNullOrWhiteSpace($bestMirror) -and $bestMs -lt [int]::MaxValue) {
    Write-Host "[DocShop] Fastest Docker mirror: $bestMirror (${bestMs}ms)" -ForegroundColor Cyan
    return $bestMirror
  }

  $fallback = $candidates[0]
  Write-Host "[DocShop] Docker mirror probe failed; fallback to mirror-first candidate: $fallback. Set DOCKER_BASE_MIRROR=off to force Docker Hub." -ForegroundColor Yellow
  return $fallback
}

function Join-ImageMirror {
  param(
    [string]$Mirror,
    [string]$Image
  )
  if ([string]::IsNullOrWhiteSpace($Mirror)) { return $Image }
  $prefix = Normalize-DockerMirrorPrefix $Mirror
  if ([string]::IsNullOrWhiteSpace($prefix)) { return $Image }
  return "$prefix/$Image"
}

$envBaseMirror = Get-DotEnvValue "DOCKER_BASE_MIRROR"
if ([string]::IsNullOrWhiteSpace($BaseMirror) -and -not [string]::IsNullOrWhiteSpace($envBaseMirror)) {
  $BaseMirror = $envBaseMirror
}

$envNodeImage = Get-DotEnvValue "NODE_IMAGE"
$envPythonImage = Get-DotEnvValue "PYTHON_IMAGE"
if (-not $env:NODE_IMAGE -and -not [string]::IsNullOrWhiteSpace($envNodeImage) -and $envNodeImage -ne $defaultNodeImage) {
  $env:NODE_IMAGE = $envNodeImage
}
if (-not $env:PYTHON_IMAGE -and -not [string]::IsNullOrWhiteSpace($envPythonImage) -and $envPythonImage -ne $defaultPythonImage) {
  $env:PYTHON_IMAGE = $envPythonImage
}

if (-not $env:NODE_IMAGE -or -not $env:PYTHON_IMAGE) {
  $mirror = $BaseMirror
  if ($mirror -and $mirror.Trim().ToLowerInvariant() -eq "off") {
    $mirror = ""
    Write-Host "[DocShop] DOCKER_BASE_MIRROR=off; using Docker Hub directly." -ForegroundColor Yellow
  } elseif ([string]::IsNullOrWhiteSpace($mirror)) {
    $mirror = Select-FastestDockerMirror
  }
  if (-not $env:NODE_IMAGE) { $env:NODE_IMAGE = Join-ImageMirror $mirror $defaultNodeImage }
  if (-not $env:PYTHON_IMAGE) { $env:PYTHON_IMAGE = Join-ImageMirror $mirror $defaultPythonImage }
}

$buildArgs = @("compose", "build")
if ($Pull) { $buildArgs += "--pull" }
if ($NoCache) { $buildArgs += "--no-cache" }
$buildArgs += $Service

Write-Host "[DocShop] BuildKit enabled" -ForegroundColor Cyan
Write-Host "[DocShop] Node base image: $env:NODE_IMAGE" -ForegroundColor Cyan
Write-Host "[DocShop] Python base image: $env:PYTHON_IMAGE" -ForegroundColor Cyan
Write-Host "[DocShop] Python packages: $env:PIP_INDEX_URL" -ForegroundColor Cyan
Write-Host "[DocShop] docker $($buildArgs -join ' ')" -ForegroundColor Cyan
& docker @buildArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Up) {
  Write-Host "[DocShop] Starting service: $Service on host port $env:DOCSHOP_PORT" -ForegroundColor Cyan
  & docker compose up -d $Service
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  Write-Host "[DocShop] Health: http://127.0.0.1:$env:DOCSHOP_PORT/health" -ForegroundColor Green
  Write-Host "[DocShop] Web:    http://127.0.0.1:$env:DOCSHOP_PORT/" -ForegroundColor Green
}
