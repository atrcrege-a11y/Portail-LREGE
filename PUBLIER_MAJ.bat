@echo off
cd /d "%~dp0"

echo ================================================
echo   Publication MAJ Portail LREGE
echo ================================================
echo.

:: ── Detecter Python ───────────────────────────────────────
set "PY="
python --version >nul 2>&1 && set "PY=python" && goto PY_OK
py --version >nul 2>&1 && set "PY=py" && goto PY_OK
python3 --version >nul 2>&1 && set "PY=python3" && goto PY_OK
echo [ERREUR] Python introuvable. Installez Python 3.9+ et cochez "Add to PATH".
pause & exit /b 1
:PY_OK
echo Python detecte : %PY%

set /p VERSION="Numero de version (ex: 9.4) : "
if "%VERSION%"=="" ( echo Erreur : version vide. & pause & exit /b 1 )

set /p DESC="Description des changements : "
if "%DESC%"=="" set DESC=Mise a jour v%VERSION%

echo.
echo --- Etape 1/6 : Mise a jour des fichiers de version ---
%PY% maj_versions.py %VERSION%
if errorlevel 1 ( echo Erreur mise a jour versions. & pause & exit /b 1 )
echo OK

echo.
echo --- Etape 2/6 : Generation setup.iss ---
%PY% generer_setup_iss.py %VERSION%
if errorlevel 1 ( echo Erreur generation setup.iss. & pause & exit /b 1 )
echo OK

echo.
echo --- Etape 3/6 : Compilation PyInstaller (PortailLREGE.exe) ---
%PY% -m PyInstaller PortailLREGE.spec --noconfirm
if errorlevel 1 (
    echo [ATTENTION] PyInstaller a echoue.
    echo Verifiez que PyInstaller est installe : %PY% -m pip install pyinstaller
    pause & exit /b 1
)
echo OK

echo.
echo --- Etape 4/6 : Compilation Inno Setup ---
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo [ATTENTION] Inno Setup 6 introuvable.
    echo Telechargez-le sur : https://jrsoftware.org/isdl.php
    echo Puis relancez ce script.
    pause & exit /b 1
) else (
    "%ISCC%" setup.iss
    if errorlevel 1 ( echo Erreur compilation Inno Setup. & pause & exit /b 1 )
    echo OK
)

set "EXE=dist\PortailLREGE_Setup_v%VERSION%.exe"
if not exist "%EXE%" (
    echo Fichier %EXE% introuvable apres compilation.
    pause & exit /b 1
)

echo.
echo --- Etape 5/6 : Sauvegarde GitHub (sources uniquement) ---
git config gc.auto 0
:: Ajouter seulement les fichiers sources, pas les artefacts de build
git add portail.py version.json setup.iss maj_versions.py generer_setup_iss.py
git add PortailLREGE.spec LANCER_PORTAIL.bat PREMIER_LANCEMENT.bat PUBLIER_MAJ.bat
git add SAUVEGARDER.bat .gitignore
:: Ajouter les modules applicatifs
git add SelecGE/ SelecMaster/ SuiviGE/ SuiviMaster/ CalendrierLREGE/ EscriTools/ SYNESC/
git add crege_app/ routes/ services/
git add -u
git commit -m "Portail v%VERSION% - %DESC%"
git push
if errorlevel 1 (
    echo [ERREUR] git push a echoue.
    echo Verifiez votre connexion et vos droits sur le depot GitHub.
    pause & exit /b 1
)
echo OK

echo.
echo --- Etape 6/6 : Publication GitHub Release ---
gh --version >nul 2>&1
if errorlevel 1 (
    echo [ATTENTION] GitHub CLI (gh) non installe.
    echo Installation automatique via winget...
    winget install --id GitHub.cli -e --silent
    if errorlevel 1 (
        echo Echec installation automatique.
        echo Installez gh manuellement : https://cli.github.com
        echo Puis authentifiez-vous avec : gh auth login
        echo.
        echo Le .exe a ete compile dans : %EXE%
        echo Creez la release manuellement sur https://github.com/atrcrege-a11y/Portail-LREGE/releases/new
        pause & exit /b 0
    )
    echo gh installe. Authentification requise :
    gh auth login
)

gh release create "v%VERSION%" "%EXE%" --title "Portail LREGE v%VERSION%" --notes "%DESC%"
if errorlevel 1 (
    echo [ERREUR] GitHub Release failed.
    echo Creez la release manuellement sur https://github.com/atrcrege-a11y/Portail-LREGE/releases/new
    echo Et uploadez : %EXE%
    pause & exit /b 1
)
echo OK

echo.
echo ================================================
echo   MAJ v%VERSION% publiee avec succes !
echo   Les utilisateurs verront la mise a jour
echo   au prochain demarrage du Portail.
echo ================================================
pause
