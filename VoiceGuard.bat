@echo off
title VoiceGuard - Audio Forensics
cd /d "%~dp0"

echo ========================================================
echo    VoiceGuard: AI Voice & Deepfake Audio Detector
echo    Digital Qazaqstan Day 2026 - IT-Generation
echo ========================================================
echo.
echo [*] Zapusk localnogo servera...

set PYTHON_CMD=
if exist runtime\python.exe set PYTHON_CMD=runtime\python.exe
if not defined PYTHON_CMD if exist .venv\Scripts\python.exe set PYTHON_CMD=.venv\Scripts\python.exe
if not defined PYTHON_CMD set PYTHON_CMD=python.exe

start "" http://127.0.0.1:7860
%PYTHON_CMD% app.py

pause
