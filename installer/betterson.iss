; Installateur Windows (Inno Setup). Construit par la CI : ISCC /DAppVersion=1.2.0 installer\betterson.iss
; Installation « par utilisateur » (sans droits administrateur) : le logiciel peut ainsi se mettre à jour seul.
; Les données (profils, mesures) vivent dans Documents\BetterSon et ne sont jamais supprimées.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{8C1F6A52-4B7E-4E0B-9B3A-BA7C0AEEC701}
AppName=BetterSon
AppVersion={#AppVersion}
AppPublisher=BetterSon
DefaultDirName={localappdata}\Programs\BetterSon
DefaultGroupName=BetterSon
PrivilegesRequired=lowest
OutputDir=..\out
OutputBaseFilename=BetterSon-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayName=BetterSon - Test de batterie

[Languages]
#if FileExists(CompilerPath + "Languages\French.isl")
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
#else
Name: "english"; MessagesFile: "compiler:Default.isl"
#endif

[Tasks]
Name: "bureau"; Description: "Créer un raccourci sur le Bureau"; Flags: checkedonce

[Files]
Source: "..\dist\BetterSon.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\BetterSon"; Filename: "{app}\BetterSon.exe"
Name: "{autodesktop}\BetterSon"; Filename: "{app}\BetterSon.exe"; Tasks: bureau

[Run]
Filename: "{app}\BetterSon.exe"; Description: "Lancer BetterSon"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\BetterSon.exe.old"
Type: files; Name: "{app}\BetterSon.exe.new"
