# PowerShell Build Script for VoiceGuard Standalone Portable Release
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path "$ScriptDir\..").Path
$DistBase = "$ProjectRoot\dist"
$BundleDir = "$DistBase\VoiceGuard-Standalone"
$ZipPath = "$DistBase\VoiceGuard-Standalone-v1.0.zip"

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "   Sborka polnogo portativnogo reliza VoiceGuard" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

# 1. Proverka iskhodnykh komponentov
$BasePython = "C:\Users\gumar\AppData\Local\Programs\Python\Python313"
$VenvSitePackages = "$ProjectRoot\.venv\Lib\site-packages"
$ModelWeights = "$ProjectRoot\models\wav2vec2-xlsr\model.safetensors"

if (!(Test-Path $BasePython)) {
    throw "Base Python not found at $BasePython"
}
if (!(Test-Path $VenvSitePackages)) {
    throw "Dependencies not found at $VenvSitePackages"
}
if (!(Test-Path $ModelWeights)) {
    throw "Model weights not found at $ModelWeights"
}

# 2. Ochistka starykh sborok
if (Test-Path $BundleDir) {
    Write-Host "[*] Ochistka predyduschego kataloga..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $BundleDir
}
if (Test-Path $ZipPath) {
    Remove-Item -Force $ZipPath
}

New-Item -ItemType Directory -Force -Path $BundleDir | Out-Null
New-Item -ItemType Directory -Force -Path "$BundleDir\models\wav2vec2-xlsr" | Out-Null
New-Item -ItemType Directory -Force -Path "$BundleDir\runtime\Lib\site-packages" | Out-Null

# 3. Kopirovanie faylov prilozheniya
Write-Host "[*] Kopirovanie prilozheniya..." -ForegroundColor Green
Copy-Item "$ProjectRoot\VoiceGuard.exe" -Destination "$BundleDir\VoiceGuard.exe"
Copy-Item "$ProjectRoot\VoiceGuard.bat" -Destination "$BundleDir\VoiceGuard.bat"
Copy-Item "$ProjectRoot\app.py" -Destination "$BundleDir\app.py"
Copy-Item "$ProjectRoot\requirements.txt" -Destination "$BundleDir\requirements.txt"
robocopy "$ProjectRoot\voiceguard" "$BundleDir\voiceguard" /E /NFL /NDL /NJH /NJS | Out-Null
robocopy "$ProjectRoot\samples" "$BundleDir\samples" /E /NFL /NDL /NJH /NJS | Out-Null

# 4. Kopirovanie vesov neyroseti
Write-Host "[*] Kopirovanie vesov modeli XLSR (~1.26 GB)..." -ForegroundColor Green
robocopy "$ProjectRoot\models\wav2vec2-xlsr" "$BundleDir\models\wav2vec2-xlsr" /E /NFL /NDL /NJH /NJS | Out-Null

# 5. Sborka portable Python runtayma
Write-Host "[*] Formirovanie avtonomnogo Python 3.13 runtayma..." -ForegroundColor Green
Copy-Item "$BasePython\python.exe" -Destination "$BundleDir\runtime\python.exe"
Copy-Item "$BasePython\pythonw.exe" -Destination "$BundleDir\runtime\pythonw.exe"
Copy-Item "$BasePython\python3*.dll" -Destination "$BundleDir\runtime\"
Copy-Item "$BasePython\vcruntime140*.dll" -Destination "$BundleDir\runtime\"
robocopy "$BasePython\DLLs" "$BundleDir\runtime\DLLs" /E /NFL /NDL /NJH /NJS | Out-Null

Write-Host "[*] Kopirovanie standartnoy biblioteki Python..." -ForegroundColor Green
robocopy "$BasePython\Lib" "$BundleDir\runtime\Lib" /E /XD "site-packages" /NFL /NDL /NJH /NJS | Out-Null

Write-Host "[*] Kopirovanie zavisimostey (PyTorch, Transformers, Gradio)..." -ForegroundColor Green
robocopy "$VenvSitePackages" "$BundleDir\runtime\Lib\site-packages" /E /NFL /NDL /NJH /NJS | Out-Null

# ._pth fayl izolyatsii
$pth = @("DLLs", "Lib", "Lib\site-packages", ".", "import site") -join "`r`n"
[System.IO.File]::WriteAllText("$BundleDir\runtime\python313._pth", $pth)

# Kopirovanie ffmpeg
$FfmpegCmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($FfmpegCmd) {
    Write-Host "[*] Dobavlenie kodeka ffmpeg.exe v runtaym..." -ForegroundColor Green
    Copy-Item $FfmpegCmd.Source -Destination "$BundleDir\runtime\ffmpeg.exe"
}

# 6. Pamyatka dlya vystupleniya
$lines = @(
    "========================================================================",
    "        VoiceGuard: AI Voice Detector - Avtonomny reliz dlya vystupleniya",
    "        Digital Qazaqstan Day 2026 | ZKITU & Batys Hub",
    "========================================================================",
    "",
    "INSTRUKTSIYA PO ZAPUSKU (V ODIN KLIK):",
    "",
    "1. Raspakuyte etot arkhiv v lyubuyu papku na kompyutere (naprimer, na Rabochiy stol).",
    "2. Zapustite fayl VoiceGuard.exe dvoynym klikom myshi.",
    "3. Cherez 2-3 sekundy avtomaticheski otkroetsya okno programmy VoiceGuard.",
    "   (Prilozhenie otkroetsya kak nastolnoe okno bez ramok brauzera).",
    "",
    "VAZHNO:",
    "- Internet NE nuzhen. Vesa neyroseti i biblioteki uzhe vstroeny vnutri papki.",
    "- Ustanavlivat Python, Git ili vvodit komandy v terminale NE nuzhno.",
    "- V papke 'samples' uzhe lezhat testovye zapisi (golos Orycha, ElevenLabs, Edge-TTS).",
    "- Dlya zakrytiya prilozheniya prosto zakroyte okno programmy krestikom.",
    "",
    "Zapasnoy variant (esli Windows blokiruet .exe):",
    "- Zapustite fayl VoiceGuard.bat.",
    "========================================================================"
)
[System.IO.File]::WriteAllLines("$BundleDir\INSTRUKTSIYA_VYSTUPLENIE.txt", $lines)

# 7. Proverka avtonomnosti sborki
Write-Host "[*] Testirovanie izolirovannogo zapuska modeli..." -ForegroundColor Cyan
& "$BundleDir\runtime\python.exe" -c "from voiceguard import detector; print('OK: Model path =', detector.MODEL_ID)"

# 8. Upakovka v ZIP
Write-Host "[*] Upakovka v ZIP-arkhiv: $ZipPath..." -ForegroundColor Yellow
Write-Host "[*] Eto mozhet zanyat 1-2 minuty iz-za szhatiya vesov modeli..." -ForegroundColor Yellow

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $BundleDir,
    $ZipPath,
    [System.IO.Compression.CompressionLevel]::Fastest,
    $false
)

$ZipSizeMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
$ZipSizeGB = [math]::Round((Get-Item $ZipPath).Length / 1GB, 2)

Write-Host "=========================================================" -ForegroundColor Green
Write-Host "   SBORKA USPESHNO ZAVERSHENA!" -ForegroundColor Green
Write-Host "   Arkhiv: $ZipPath" -ForegroundColor Green
Write-Host "   Razmer: $ZipSizeMB MB ($ZipSizeGB GB)" -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Green
