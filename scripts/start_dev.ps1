param(
  [string]$BackendHost = "127.0.0.1",
  [int]$BackendPort = 8000,
  [string]$FrontendHost = "127.0.0.1",
  [int]$FrontendPort = 3000,
  [switch]$InstallDeps
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$BackendPidFile = Join-Path $BackendDir ".dev-backend.pid"
$FrontendPidFile = Join-Path $FrontendDir ".dev-frontend.pid"
$BackendLogDir = Join-Path $BackendDir "logs"
$BackendLog = Join-Path $BackendLogDir "dev-backend.log"
$BackendErrLog = Join-Path $BackendLogDir "dev-backend.err.log"
$FrontendLog = Join-Path $FrontendDir "dev-frontend.log"
$FrontendErrLog = Join-Path $FrontendDir "dev-frontend.err.log"
$NpmCommand = (Get-Command "npm.cmd" -ErrorAction SilentlyContinue)
if (-not $NpmCommand) {
  $NpmCommand = (Get-Command "npm" -ErrorAction SilentlyContinue)
}
if (-not $NpmCommand) {
  throw "npm is not available in PATH"
}
$NpmExe = $NpmCommand.Source

function Test-PortOpen([int]$Port) {
  $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  return $null -ne $conn
}

function Test-PidAlive([string]$PidFile) {
  if (-not (Test-Path $PidFile)) { return $false }
  $pidText = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
  if (-not $pidText) { return $false }
  $proc = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
  return $null -ne $proc
}

New-Item -ItemType Directory -Force -Path $BackendLogDir | Out-Null

$MigrationScript = Join-Path $Root "scripts\migrate_sqlite_layout.py"
if (Test-Path $MigrationScript) {
  & python $MigrationScript --root $Root
}

if ($InstallDeps) {
  Push-Location $FrontendDir
  try { & $NpmExe install } finally { Pop-Location }
}

if ((Test-PidAlive $BackendPidFile) -or (Test-PortOpen $BackendPort)) {
  Write-Output "Backend already running: http://$BackendHost`:$BackendPort"
} else {
  $backendArgs = "-m uvicorn app.main:app --host $BackendHost --port $BackendPort"
  $backend = Start-Process -FilePath "python" -ArgumentList $backendArgs -WorkingDirectory $BackendDir -RedirectStandardOutput $BackendLog -RedirectStandardError $BackendErrLog -PassThru -WindowStyle Hidden
  Set-Content -Path $BackendPidFile -Value $backend.Id -Encoding ASCII
  Write-Output "Backend started PID=$($backend.Id): http://$BackendHost`:$BackendPort"
}

if ((Test-PidAlive $FrontendPidFile) -or (Test-PortOpen $FrontendPort)) {
  Write-Output "Frontend already running: http://$FrontendHost`:$FrontendPort"
} else {
  $frontendArgs = "run dev -- --host $FrontendHost --port $FrontendPort"
  $frontend = Start-Process -FilePath $NpmExe -ArgumentList $frontendArgs -WorkingDirectory $FrontendDir -RedirectStandardOutput $FrontendLog -RedirectStandardError $FrontendErrLog -PassThru -WindowStyle Hidden
  Set-Content -Path $FrontendPidFile -Value $frontend.Id -Encoding ASCII
  Write-Output "Frontend started PID=$($frontend.Id): http://$FrontendHost`:$FrontendPort"
}

Write-Output ""
Write-Output "Open: http://$FrontendHost`:$FrontendPort/"
Write-Output "API : http://$BackendHost`:$BackendPort/docs"
