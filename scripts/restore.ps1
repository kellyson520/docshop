# DocShop Restore Script
# Usage: .\scripts\restore.ps1 data\backups\20260603_120000

param([string]$BackupDir)

if (-not $BackupDir) {
    Write-Host "Usage: restore.ps1 BACKUP_DIR"
    Write-Host "       e.g. restore.ps1 data\backups\20260603_120000"
    exit 1
}

$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root $BackupDir

if (-not (Test-Path $src)) {
    Write-Host "ERROR: Backup not found: $src"
    exit 1
}

Write-Host "WARNING: This will overwrite current data. Stop backend first."
$confirm = Read-Host "Continue? (y/n)"
if ($confirm -ne 'y') { exit }

$dataDir = "$root\backend\data"

# DB
if (Test-Path "$src\docshop.db") {
    Copy-Item "$src\docshop.db" "$dataDir\docshop.db" -Force
    Write-Host "  DB restored"
}

# Uploads
if (Test-Path "$src\uploads") {
    Copy-Item "$src\uploads\*" "$dataDir\uploads" -Recurse -Force
    Write-Host "  Uploads restored"
}

# Documents
if (Test-Path "$src\documents") {
    Copy-Item "$src\documents\*" "$dataDir\documents" -Recurse -Force
    Write-Host "  Documents restored"
}

Write-Host "Restore complete. Restart backend."


