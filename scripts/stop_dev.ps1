param(
  [switch]$Force,
  [int[]]$Ports = @(3000, 8000)
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$PidFiles = @(
  (Join-Path $Root "backend\.dev-backend.pid"),
  (Join-Path $Root "frontend\.dev-frontend.pid")
)

function Stop-PidFile([string]$PidFile) {
  if (-not (Test-Path $PidFile)) { return }
  $pidText = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
  if ($pidText) {
    $proc = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
    if ($proc) {
      Stop-Process -Id $proc.Id -Force:$Force
      Write-Output "Stopped PID=$($proc.Id) from $PidFile"
    }
  }
  Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}

foreach ($pidFile in $PidFiles) {
  Stop-PidFile $pidFile
}

foreach ($port in $Ports) {
  $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  foreach ($listener in $listeners) {
    $owningPid = $listener.OwningProcess
    $proc = Get-Process -Id $owningPid -ErrorAction SilentlyContinue
    if ($proc -and ($proc.ProcessName -match "^(python|node|npm)$")) {
      Stop-Process -Id $owningPid -Force:$Force
      Write-Output "Stopped $($proc.ProcessName) PID=$owningPid on port $port"
    }
  }
}
