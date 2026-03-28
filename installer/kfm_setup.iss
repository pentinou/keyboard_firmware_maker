; Inno Setup Script — Keyboard Firmware Maker
; Compile avec Inno Setup 6+ : https://jrsoftware.org/isinfo.php
;
; Prerequis : avoir lance scripts/build_windows.bat pour generer
; le dossier dist/KeyboardFirmwareMaker/

#define MyAppName "Keyboard Firmware Maker"
#define MyAppExeName "KeyboardFirmwareMaker.exe"
#define MyAppPublisher "Pentinou"
#define MyAppURL "https://github.com/Pentinou/keyboard_firmware_maker"

; Lire la version depuis _version.py (fallback 0.1.0)
#define VersionFile "..\dist\KeyboardFirmwareMaker\_version.py"
#ifexist VersionFile
  #define MyAppVersion ReadIni(VersionFile, "", "__version__", "0.1.0")
#else
  #define MyAppVersion "0.1.0"
#endif

[Setup]
AppId={{A7E3F4B2-9C1D-4E5F-8A2B-6D0E1F3C7890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=KeyboardFirmwareMaker_Setup_{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Decommenter quand l'icone .ico sera disponible :
; SetupIconFile=..\assets\icons\kfm.ico
; UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\KeyboardFirmwareMaker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
