@echo off
setlocal
title Haven Model Lab
cd /d "%~dp0"
if not exist "%~dp0.local\python\python.exe" (
 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap.ps1" -RuntimeOnly
 if errorlevel 1 goto failed
)
call "%~dp0OPEN-LAB.cmd"
exit /b %errorlevel%
:failed
echo.
echo Setup did not finish. Read the error above; no engine was silently changed.
pause
exit /b 1
