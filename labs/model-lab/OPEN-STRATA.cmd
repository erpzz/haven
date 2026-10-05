@echo off
setlocal
cd /d "%~dp0"
echo Starting Strata. The browser opens after the model is ready.
echo Use STOP-STRATA.cmd for native unload and full shutdown.
"%~dp0.local\python\python.exe" -X utf8 "%~dp0launcher.py" strata
if errorlevel 1 pause
