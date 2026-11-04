; Installateur Windows (Inno Setup). Construit par la CI : ISCC /DAppVersion=1.2.0 installer\batconnect.iss
; Installation « par utilisateur » (sans droits administrateur) : le logiciel peut ainsi se mettre à jour seul.
; Les données (profils, mesures) vivent dans Documents\BatConnect et ne sont jamais supprimées.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{8C1F6A52-4B7E-4E0B-9B3A-BA7C0AEEC701}
AppName=BatConnect
AppVersion={#AppVersion}
AppPublisher=BatConnect
DefaultDirName={localappdata}\Programs\BatConnect
DefaultGroupName=BatConnect
PrivilegesRequired=lowest
OutputDir=..\out
OutputBaseFilename=BatConnect-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayName=BatConnect - Test de batterie

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "bureau"; Description: "Créer un raccourci sur le Bureau"; Flags: checkedonce

[Files]
Source: "..\dist\BatConnect.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\BatConnect"; Filename: "{app}\BatConnect.exe"
Name: "{autodesktop}\BatConnect"; Filename: "{app}\BatConnect.exe"; Tasks: bureau

[Run]
Filename: "{app}\BatConnect.exe"; Description: "Lancer BatConnect"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\BatConnect.exe.old"
Type: files; Name: "{app}\BatConnect.exe.new"
