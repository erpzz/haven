@echo off
setlocal
title Haven Model Lab
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap.ps1"
if errorlevel 1 (
 echo.
 echo Setup did not finish. Read the error above; no engine was silently changed.
 pause
)
