@echo off
setlocal
cd /d "%~dp0"
echo Starting Haven Model Lab. The browser opens when ready.
echo Keep this window open, or use STOP-LAB.cmd when finished.
"%~dp0.local\python\python.exe" -X utf8 "%~dp0launcher.py" lab
if errorlevel 1 pause
