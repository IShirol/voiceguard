[CmdletBinding()]
param(
    [string]$OutZip = "dist\VoiceGuard-Portable.zip",
    [switch]$IncludeVenv
)

$ErrorActionPreference = "Stop"
$root = (Get-Item $PSScriptRoot).Parent.FullName

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Build VoiceGuard Portable Package      " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Project root: $root"

# 1. Compile VoiceGuard.exe if missing
$exePath = Join-Path $root "VoiceGuard.exe"
if (-not (Test-Path $exePath)) {
    Write-Host "[!] VoiceGuard.exe not found. Compiling..." -ForegroundColor Yellow
    $csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    $icon = Join-Path $root "tools\launcher\app.ico"
    $src = Join-Path $root "tools\launcher\VoiceGuardLauncher.cs"
    & $csc /target:winexe /optimize+ /win32icon:$icon /r:System.dll /r:System.Drawing.dll /r:System.Windows.Forms.dll /out:$exePath $src
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to compile VoiceGuard.exe"
    }
}

# 2. Prepare staging
$distDir = Join-Path $root "dist"
$stageDir = Join-Path $distDir "VoiceGuard-Stage"

if (Test-Path $stageDir) {
    Remove-Item $stageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $stageDir -Force | Out-Null

Write-Host "[1/4] Copying launcher and configs..." -ForegroundColor Green
Copy-Item (Join-Path $root "VoiceGuard.exe") -Destination $stageDir
Copy-Item (Join-Path $root "VoiceGuard.bat") -Destination $stageDir
Copy-Item (Join-Path $root "app.py") -Destination $stageDir
Copy-Item (Join-Path $root "requirements.txt") -Destination $stageDir
Copy-Item (Join-Path $root "README.md") -Destination $stageDir

Write-Host "[2/4] Copying modules and samples..." -ForegroundColor Green
Copy-Item (Join-Path $root "voiceguard") -Destination $stageDir -Recurse
Copy-Item (Join-Path $root "samples") -Destination $stageDir -Recurse
Copy-Item (Join-Path $root "tools") -Destination $stageDir -Recurse

# Clean __pycache__ in staging
Get-ChildItem -Path $stageDir -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $stageDir -Recurse -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue

# Include venv as portable runtime if requested
if ($IncludeVenv) {
    $venvPath = Join-Path $root ".venv"
    if (Test-Path $venvPath) {
        Write-Host "[*] Bundling .venv as portable runtime..." -ForegroundColor Yellow
        $runtimeTarget = Join-Path $stageDir "runtime"
        Copy-Item $venvPath -Destination $runtimeTarget -Recurse
    }
}

# 3. Create README_PORTABLE.txt
$readmeLines = @(
    "========================================================================",
    "                      VOICEGUARD - AI VOICE DETECTOR",
    "                       Standalone 1-Click Launch",
    "========================================================================",
    "",
    "Quick Start:",
    "  1. Double click 'VoiceGuard.exe'.",
    "  2. Splash screen appears and initializes the AI detector.",
    "  3. VoiceGuard interface opens in Microsoft Edge App Mode at http://127.0.0.1:7860/.",
    "  4. To exit, close the Edge window or right-click the tray icon and select Stop.",
    "",
    "Requirements:",
    "  - Windows 10 / 11 (x64)",
    "  - Python 3.10+ installed or local .venv folder.",
    "  - If not configured yet, run:",
    "      python -m venv .venv",
    "      .venv\Scripts\pip install -r requirements.txt",
    "",
    "Offline / Full Portable:",
    "  - You can place an embedded/standalone Python environment into 'runtime\'.",
    "  - VoiceGuardLauncher will automatically prioritize 'runtime\python.exe'.",
    "",
    "Test Samples:",
    "  - samples\orych_voice_real.ogg (Real human speech)",
    "  - samples\fake_edge_tts.mp3 (Synthetic audio)",
    "  - samples\fake_elevenlabs_orych.mp3 (Cloned AI voice)",
    "========================================================================"
)
[System.IO.File]::WriteAllLines((Join-Path $stageDir "README_PORTABLE.txt"), $readmeLines, [System.Text.Encoding]::UTF8)

Write-Host "[3/4] Creating ZIP package: $OutZip..." -ForegroundColor Green
$targetZipFullPath = [System.IO.Path]::GetFullPath((Join-Path $root $OutZip))
$targetZipParent = Split-Path $targetZipFullPath -Parent
if (-not (Test-Path $targetZipParent)) {
    New-Item -ItemType Directory -Path $targetZipParent -Force | Out-Null
}
if (Test-Path $targetZipFullPath) {
    Remove-Item $targetZipFullPath -Force
}

Compress-Archive -Path "$stageDir\*" -DestinationPath $targetZipFullPath -CompressionLevel Optimal

Write-Host "[4/4] Cleaning temporary staging..." -ForegroundColor Green
Remove-Item $stageDir -Recurse -Force

$zipItem = Get-Item $targetZipFullPath
$sizeMb = [math]::Round($zipItem.Length / 1MB, 2)
$hash = (Get-FileHash $targetZipFullPath -Algorithm SHA256).Hash

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Build completed successfully!          " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Archive: $targetZipFullPath"
Write-Host "Size:    $sizeMb MB ($($zipItem.Length) bytes)"
Write-Host "SHA256:  $hash"
