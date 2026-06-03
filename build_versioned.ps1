param(
    [switch]$NoBump
)

$ErrorActionPreference = 'Stop'

$pythonCandidates = @(
    'C:\Users\zipsh\AppData\Local\Programs\Python\Python312\python.exe',
    'C:\Users\zipsh\AppData\Local\Programs\Python\Python314\python.exe'
)
$python = $pythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $python) {
    throw "Python not found. Tried: $($pythonCandidates -join ', ')"
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

$bundleName = 'MediaFetchAIA'
$releaseName = "${bundleName}.exe"
$releaseExe = Join-Path $releaseRoot $releaseName
$releaseMain = Join-Path $root "dist\main\${releaseName}"
$releaseInternal = Join-Path $releaseRoot '_internal'
$legacyReleaseNames = @(
    (Join-Path $releaseRoot 'VideoDownloader_codex.exe'),
    (Join-Path $root 'dist\main\VideoDownloader_codex.exe'),
    (Join-Path $releaseRoot 'YouTubeDownloader_codex.exe'),
    (Join-Path $root 'dist\main\YouTubeDownloader_codex.exe')
)

foreach ($legacyRelease in $legacyReleaseNames) {
    if (Test-Path $legacyRelease) {
        Remove-Item -Path $legacyRelease -Force
    }
}

if (Test-Path $releaseInternal) {
    Remove-Item -Path $releaseInternal -Recurse -Force
}
Copy-Item -Path $mainInternal -Destination $releaseInternal -Recurse -Force

Copy-Item -Path $mainExe -Destination $releaseExe -Force
Copy-Item -Path $mainExe -Destination $releaseMain -Force

Write-Host "Done."
Write-Host "- main: $mainExe"
Write-Host "- release copy (dist/main): $releaseMain"
Write-Host "- release exe (dist/releases): $releaseExe"
Write-Host "- release dependencies: $releaseInternal"
