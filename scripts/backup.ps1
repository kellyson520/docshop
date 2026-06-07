# DocDist Backup Script
# Usage: .\scripts\backup.ps1

$root = Split-Path -Parent $PSScriptRoot
$backupRoot = "$root\data\backups"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "$backupRoot\$ts"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] Starting backup to $backupDir"

# 1. SQLite DB
$db = "$root\backend\data\docdist.db"
if (Test-Path $db) {
    Copy-Item $db "$backupDir\docdist.db"
    Write-Host "  DB backed up ($((Get-Item $db).Length) bytes)"
} else { Write-Host "  WARNING: DB not found" }

# 2. Uploads
$up = "$root\backend\data\uploads"
if (Test-Path $up) {
    Copy-Item $up "$backupDir\uploads" -Recurse -Force
    Write-Host "  Uploads backed up"
} else { Write-Host "  WARNING: uploads not found" }

# 3. Documents (triple-layer)
$docs = "$root\backend\data\documents"
if (Test-Path $docs) {
    Copy-Item $docs "$backupDir\documents" -Recurse -Force
    Write-Host "  Documents backed up"
}

# 4. Meta
@" 
Backup: $ts
Source: $root
"@ | Out-File "$backupDir\BACKUP_INFO.txt"

# 5. Clean old (>7 days)
Get-ChildItem $backupRoot -Directory | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item -Recurse -Force
Write-Host "  Old backups cleaned"

Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] Done: $backupDir"
