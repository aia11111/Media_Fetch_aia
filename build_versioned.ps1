param(
    [switch]$NoBump
)

$ErrorActionPreference = 'Stop'

$python = 'C:\Users\zipsh\AppData\Local\Programs\Python\Python314\python.exe'
if (-not (Test-Path $python)) {
    throw "Python not found: $python"
}

$root = $PSScriptRoot
$versionFile = Join-Path $root 'VERSION'
if (-not (Test-Path $versionFile)) {
    '00' | Set-Content -Path $versionFile -Encoding UTF8
}

$versionText = (Get-Content -Path $versionFile -Raw).Trim()
$versionNumber = $null

if ($versionText -match '^\d+$') {
    $versionNumber = [int]$versionText
}
elseif ($versionText -match '^(\d+)\.(\d+)\.(\d+)$') {
    # Legacy 1.0.x format: keep the patch number as the rolling release number.
    $versionNumber = [int]$matches[3]
}
else {
    throw "Invalid VERSION format: $versionText"
}

if (-not $NoBump) {
    $versionNumber += 1
}

$newVersion = '{0:D2}' -f $versionNumber
$newVersion | Set-Content -Path $versionFile -Encoding UTF8

Write-Host "Building version $newVersion ..."
& $python -m PyInstaller --noconfirm main.spec

$mainDir = Join-Path $root 'dist\main'
$mainExe = Join-Path $mainDir 'main.exe'
$mainInternal = Join-Path $mainDir '_internal'
if (-not (Test-Path $mainExe)) {
    throw "Build output not found: $mainExe"
}
if (-not (Test-Path $mainInternal)) {
    throw "Build dependency folder not found: $mainInternal"
}

$releaseRoot = Join-Path $root 'dist\releases'
New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null

$bundleName = 'YouTubeDownloader_codex'
$releaseName = "${bundleName}.exe"
$releaseBundleDir = Join-Path $releaseRoot $bundleName
$releaseExe = Join-Path $releaseBundleDir $releaseName
$releaseMain = Join-Path $root "dist\main\${releaseName}"
$releaseInternal = Join-Path $releaseBundleDir '_internal'

New-Item -ItemType Directory -Force -Path $releaseBundleDir | Out-Null
if (Test-Path $releaseInternal) {
    Remove-Item -Path $releaseInternal -Recurse -Force
}
Copy-Item -Path $mainInternal -Destination $releaseInternal -Recurse -Force

Copy-Item -Path $mainExe -Destination $releaseExe -Force
Copy-Item -Path $mainExe -Destination $releaseMain -Force

Write-Host "Done."
Write-Host "- main: $mainExe"
Write-Host "- release copy (dist/main): $releaseMain"
Write-Host "- bundle (dist/releases): $releaseBundleDir"
Write-Host "- release exe (dist/releases): $releaseExe"
Write-Host "- release dependencies: $releaseInternal"
