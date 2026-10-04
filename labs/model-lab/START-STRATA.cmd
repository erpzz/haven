@echo off
setlocal
title Strata - local inference
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0strata-setup.ps1" -StartOnly
pause
