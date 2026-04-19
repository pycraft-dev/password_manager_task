# Release build: PyInstaller + ZIP for distribution.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$ver = (Get-Content -Path (Join-Path $Root "VERSION") -Raw).Trim() -replace "`r|`n", ""
if (-not $ver) { $ver = "0.0.0" }

Write-Host "Version: $ver"
python -m PyInstaller build_exe.spec --noconfirm
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$releaseDir = Join-Path $Root "release"
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
$zipName = "PasswordManager-${ver}-win64.zip"
$zipPath = Join-Path $releaseDir $zipName
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

$exe = Join-Path $Root "dist\PasswordManager.exe"
if (-not (Test-Path $exe)) {
    Write-Error "Missing: $exe"
    exit 1
}

$staging = Join-Path $releaseDir "staging_$ver"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path $staging | Out-Null
Copy-Item $exe $staging
Copy-Item (Join-Path $Root "LICENSE") $staging
$clientMd = Get-ChildItem -LiteralPath $Root -Filter "README_*.md" -File | Where-Object { $_.Name -ne "README.md" } | Select-Object -First 1
if (-not $clientMd) { Write-Error "Client README (README_*.md) not found"; exit 1 }
Copy-Item $clientMd.FullName $staging
Copy-Item (Join-Path $Root ".env.example") $staging
Copy-Item (Join-Path $Root "CHANGELOG.md") $staging

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipPath -Force
Remove-Item $staging -Recurse -Force

Write-Host "Done: $zipPath"
