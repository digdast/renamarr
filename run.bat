@echo off
title Renamarr - Interactive Media Renamer & Organizer
cls
echo ====================================================================
echo   ⚡ Renamarr - Next-Gen Interactive Media Renamer ^& Organizer
echo ====================================================================
echo.
echo Starting Renamarr Web Dashboard on http://localhost:7879 ...
echo.

start "" "http://localhost:7879"
python -m uvicorn app.main:app --host 0.0.0.0 --port 7879 --app-dir "%~dp0"
pause
