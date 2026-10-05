@echo off
setlocal
cd /d "%~dp0"
"%~dp0.local\python\python.exe" -X utf8 "%~dp0launcher.py" lab --stop
if errorlevel 1 pause
