@echo off
echo Starting Instagram Automation Tool...
echo.
cd /d "%~dp0"
.venv\Scripts\python.exe src\main.py
echo.
echo Application closed.
pause 