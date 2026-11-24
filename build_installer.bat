@echo off
chcp 65001 >nul
cd /d "%~dp0"
call build_all.bat
where iscc >nul 2>nul && (iscc installer.iss & echo تم: dist\JarvisArabic-Setup.exe) || echo لإنشاء ملف التثبيت ثبّت Inno Setup من jrsoftware.org ثم شغّل هذا الملف مرة ثانية
pause
