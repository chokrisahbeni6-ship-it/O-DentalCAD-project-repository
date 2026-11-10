# Sauvegarde DentalCAD (Windows PowerShell). À lancer depuis le dossier du projet :
#   powershell -ExecutionPolicy Bypass -File scripts\backup.ps1
# Programmez-le chaque jour via le "Planificateur de tâches" Windows.
# IMPORTANT : copiez ensuite le dossier "backups" sur un disque externe CHIFFRÉ
# (BitLocker) et TESTEZ une restauration au moins une fois.
$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$dir = Join-Path (Get-Location) "backups"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

# 1) Base de données
docker compose exec -T postgres pg_dump -U dentalcad -Fc dentalcad -f /tmp/db.dump
docker compose cp postgres:/tmp/db.dump "$dir\db-$stamp.dump"

# 2) Images DICOM (Orthanc)
docker run --rm -v dentalcad_orthanc_data:/d -v "${dir}:/b" alpine `
    tar czf "/b/orthanc-$stamp.tgz" -C /d .

# 3) Garder 30 jours
Get-ChildItem $dir | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item
Write-Host "Sauvegarde terminée : $dir ($stamp)"
