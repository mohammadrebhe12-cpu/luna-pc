@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === تثبيت JARVIS ARABIC ===
where py >nul 2>nul || (echo [خطأ] Python غير مثبت. ثبّت Python 3.11 او 3.12 من python.org وفعّل Add to PATH & pause & exit /b 1)
if not exist .venv py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || (echo [خطأ] فشل التثبيت & pause & exit /b 1)
echo.
echo تم التثبيت. شغّل التطبيق بالملف run.bat
pause
