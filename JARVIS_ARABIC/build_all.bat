@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === بناء JARVIS ARABIC كبرنامج EXE (نقرة وحدة) ===
where python >nul 2>nul || (echo [خطأ] ثبّت Python 3.12 من python.org مع Add to PATH ثم اعد التشغيل & pause & exit /b 1)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller || (echo [خطأ] فشل التثبيت & pause & exit /b 1)
pyinstaller --noconfirm --clean jarvis.spec || (echo [خطأ] فشل البناء & pause & exit /b 1)
echo.
echo تم! افتح المجلد dist\JarvisArabic وشغّل JarvisArabic.exe
echo (تقدر تنسخ المجلد كامل لسطح المكتب، وما بتحتاج Python بعد هيك)
start "" dist\JarvisArabic

