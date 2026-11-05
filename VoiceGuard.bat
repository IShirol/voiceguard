@echo off
title VoiceGuard - Audio Forensics
cd /d "%~dp0"

echo ========================================================
echo    VoiceGuard: AI Voice & Deepfake Audio Detector
echo    Digital Qazaqstan Day 2026 - IT-Generation
echo ========================================================
echo.
echo [*] Zapusk localnogo servera...

if not exist .venv\Scripts\python.exe (
    echo [ERROR] Virtualnoe okruzhenie .venv ne naydeno!
    pause
    exit /b
)

start "" http://127.0.0.1:7860
.venv\Scripts\python.exe app.py

pause
