@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv (echo شغّل install.bat اولا & pause & exit /b 1)
call .venv\Scripts\activate.bat
pip install pyinstaller || exit /b 1
pyinstaller --noconfirm --clean jarvis.spec || (echo [خطأ] فشل البناء & pause & exit /b 1)
echo.
echo تم! الملف: dist\JarvisArabic\JarvisArabic.exe  (انسخ المجلد dist\JarvisArabic كاملا)
pause
