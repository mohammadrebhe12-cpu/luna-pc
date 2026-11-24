# PyInstaller spec — pyinstaller --noconfirm --clean jarvis.spec
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [("assets", "assets")], [], []
for pkg in ["faster_whisper", "ctranslate2", "onnxruntime", "av", "edge_tts", "yt_dlp",
            "pycaw", "comtypes", "pyttsx3", "sounddevice", "_sounddevice_data", "mss"]:
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception as e:
        print("skip", pkg, e)

a = Analysis(["main.py"], pathex=["."], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             excludes=["tkinter", "matplotlib", "PyQt5", "PyQt6", "pytest", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
                       "PySide6.Qt3DCore", "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtPdf", "PySide6.QtCharts",
                       "PySide6.QtDataVisualization", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtBluetooth"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="JarvisArabic", console=False,
          icon="assets/icon.ico")
coll = COLLECT(exe, a.binaries, a.datas, name="JarvisArabic")
