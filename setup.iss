; ================================================================
;  Portail LREGE - Installeur Inno Setup
;  Version : 1.0.0
;  Editeur : Escrime Grand Est
; ================================================================

#define AppName    "Portail LREGE"
#define AppVersion "1.1.0"
#define AppPublisher "Escrime Grand Est"
#define AppURL     "https://www.lrege.fr"

[Setup]
AppId={{B4F2A3C1-7E9D-4A2B-8C6F-1D3E5F7A9B2C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL={#AppURL}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\LREGE\Portail
DefaultGroupName={#AppName}
AllowNoIcons=no
OutputDir=dist
OutputBaseFilename=PortailLREGE_Setup_v{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableDirPage=no
DisableWelcomePage=no
SetupIconFile=portail.ico
UninstallDisplayIcon={app}\portail.ico

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
Source: "portail.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "portail.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "LANCER_PORTAIL.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "PREMIER_LANCEMENT.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "SelecGE\*"; DestDir: "{app}\SelecGE"; Flags: ignoreversion recursesubdirs
Source: "SYNESC\*"; DestDir: "{app}\SYNESC"; Flags: ignoreversion recursesubdirs
Source: "EscriTools\*"; DestDir: "{app}\EscriTools"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\LANCER_PORTAIL.bat"; WorkingDir: "{app}"; IconFilename: "{app}\portail.ico"
Name: "{group}\Desinstaller {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\LANCER_PORTAIL.bat"; WorkingDir: "{app}"; IconFilename: "{app}\portail.ico"

[Run]
Filename: "{app}\PREMIER_LANCEMENT.bat"; Description: "Installer les dependances (recommande)"; Flags: postinstall runasoriginaluser shellexec; Check: PremierLancement

[Code]
function PremierLancement(): Boolean;
begin
  Result := not FileExists(ExpandConstant('{app}\SYNESC\.venv\Scripts\python.exe'));
end;

[UninstallDelete]
Type: filesandordirs; Name: "{app}\SYNESC\.venv"
Type: filesandordirs; Name: "{app}\__pycache__"
