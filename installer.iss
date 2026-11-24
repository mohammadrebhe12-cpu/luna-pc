; Inno Setup — يبني JarvisArabic-Setup.exe من مجلد dist\JarvisArabic
#define AppName "العمد PC"
#define AppVer "1.0.0"
[Setup]
AppId={{6F1B7C52-9A0E-4B7E-8E3A-4A1D5C0E7A11}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=JARVIS ARABIC
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=JarvisArabic-Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\JarvisArabic.exe
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
[Tasks]
Name: "desktopicon"; Description: "اختصار على سطح المكتب / Desktop shortcut"; Flags: checkedonce
Name: "startup"; Description: "تشغيل مع ويندوز / Start with Windows"; Flags: unchecked
[Files]
Source: "dist\JarvisArabic\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\JarvisArabic.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\JarvisArabic.exe"; Tasks: desktopicon
[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "JarvisArabic"; ValueData: """{app}\JarvisArabic.exe"" --minimized"; Tasks: startup; Flags: uninsdeletevalue
[Run]
Filename: "{app}\JarvisArabic.exe"; Description: "تشغيل جارفيس الآن"; Flags: nowait postinstall skipifsilent
