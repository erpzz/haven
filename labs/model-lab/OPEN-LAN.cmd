@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1" -Kind lab -Lan
if errorlevel 1 pause
