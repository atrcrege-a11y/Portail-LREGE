# -*- coding: utf-8 -*-
"""
generer_setup_iss.py
Génère setup.iss automatiquement depuis portail.py.
Appeler avant ISCC.exe dans PUBLIER_MAJ.bat.

Usage : python generer_setup_iss.py <version>
"""

import sys, re, os

def extraire_version(portail_src):
    m = re.search(r'VERSION_LOCALE\s*=\s*"([^"]+)"', portail_src)
    return m.group(1) if m else "0.0.0"

def extraire_outils(portail_src):
    """Extrait les clés de OUTILS et les dossiers associés (type web/tkinter)."""
    # On cherche toutes les entrées de OUTILS avec leur cwd et type
    outils = []
    # Regex : bloc par outil
    blocs = re.findall(
        r'"(\w+)":\s*\{[^}]+?"script":\s*os\.path\.join\(BASE_DIR,\s*"([^"]+)"[^}]+?"type":\s*"([^"]+)"',
        portail_src, re.DOTALL
    )
    for oid, dossier, typ in blocs:
        outils.append({'id': oid, 'dossier': dossier, 'type': typ})
    return outils

def generer_iss(version, outils):
    # Section [Files] dynamique
    files_statiques = """\
Source: "portail.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "portail.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "LANCER_PORTAIL.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "PREMIER_LANCEMENT.bat"; DestDir: "{app}"; Flags: ignoreversion"""

    files_outils = ""
    for o in outils:
        d = o['dossier']
        files_outils += f'\nSource: "{d}\\*"; DestDir: "{{app}}\\{d}"; Flags: ignoreversion recursesubdirs; Excludes: "*.pyc,__pycache__"'

    iss = f"""; ================================================================
;  Portail LREGE - Installeur Inno Setup
;  Genere automatiquement par generer_setup_iss.py
;  Version : {version}
;  Editeur : Escrime Grand Est
; ================================================================

#define AppName    "Portail LREGE"
#define AppVersion "{version}"
#define AppPublisher "Escrime Grand Est"
#define AppURL     "https://www.lrege.fr"

[Setup]
AppId={{{{B4F2A3C1-7E9D-4A2B-8C6F-1D3E5F7A9B2C}}}}
AppName={{#AppName}}
AppVersion={{#AppVersion}}
AppPublisherURL={{#AppURL}}
AppPublisher={{#AppPublisher}}
DefaultDirName={{autopf}}\\LREGE\\Portail
DefaultGroupName={{#AppName}}
AllowNoIcons=no
OutputDir=dist
OutputBaseFilename=PortailLREGE_Setup_v{{#AppVersion}}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableDirPage=no
DisableWelcomePage=no
SetupIconFile=portail.ico
UninstallDisplayIcon={{app}}\\portail.ico

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\\French.isl"

[Files]
{files_statiques}{files_outils}

[Icons]
Name: "{{group}}\\{{#AppName}}"; Filename: "{{app}}\\LANCER_PORTAIL.bat"; WorkingDir: "{{app}}"; IconFilename: "{{app}}\\portail.ico"
Name: "{{group}}\\Desinstaller {{#AppName}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{{#AppName}}"; Filename: "{{app}}\\LANCER_PORTAIL.bat"; WorkingDir: "{{app}}"; IconFilename: "{{app}}\\portail.ico"

[Run]
Filename: "{{app}}\\PREMIER_LANCEMENT.bat"; Description: "Installer les dependances (recommande)"; Flags: postinstall runasoriginaluser shellexec; Check: PremierLancement
Filename: "{{app}}\\LANCER_PORTAIL.bat"; Description: "Relancer le Portail LREGE"; Flags: postinstall runasoriginaluser shellexec nowait; WorkingDir: "{{app}}"

[Code]
function PremierLancement(): Boolean;
begin
  Result := not FileExists(ExpandConstant('{{app}}\\SYNESC\\.venv\\Scripts\\python.exe'));
end;

[UninstallDelete]
Type: filesandordirs; Name: "{{app}}\\SYNESC\\.venv"
Type: filesandordirs; Name: "{{app}}\\__pycache__"
"""
    return iss

def main():
    version = sys.argv[1] if len(sys.argv) > 1 else None

    portail_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'portail.py')
    with open(portail_path, encoding='utf-8') as f:
        src = f.read()

    if not version:
        version = extraire_version(src)

    outils = extraire_outils(src)
    if not outils:
        print("ERREUR : aucun outil trouvé dans portail.py")
        sys.exit(1)

    print(f"Version     : {version}")
    print(f"Outils ({len(outils)}) : {', '.join(o['id'] for o in outils)}")

    iss = generer_iss(version, outils)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'setup.iss')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(iss)
    print(f"setup.iss généré → {out}")

if __name__ == '__main__':
    main()
