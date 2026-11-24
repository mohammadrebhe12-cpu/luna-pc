@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\pythonw.exe (echo شغّل install.bat اولا & pause & exit /b 1)
start "" .venv\Scripts\pythonw.exe main.py
