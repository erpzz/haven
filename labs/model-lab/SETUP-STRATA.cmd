@echo off
setlocal
title Strata - explicit setup
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0strata-setup.ps1"
pause
