@echo off
cd /d "%~dp0"

:: ── Log toutes les sorties dans un fichier ─────────────────────
set "LOG=%~dp0publier_maj_log.txt"
echo === PUBLIER_MAJ %date% %time% === > "%LOG%"
echo Dossier : %CD% >> "%LOG%"

echo ================================================
echo   Publication MAJ Portail LREGE
echo ================================================
echo.

:: ── Supprimer le verrou git si présent ────────────────────────
if exist ".git\index.lock" del /f ".git\index.lock" >> "%LOG%" 2>&1

:: ── Detecter Python ───────────────────────────────────────────
set "PY="
python --version >nul 2>&1 && set "PY=python" && goto PY_OK
py --version >nul 2>&1 && set "PY=py" && goto PY_OK
python3 --version >nul 2>&1 && set "PY=python3" && goto PY_OK
echo [ERREUR] Python introuvable >> "%LOG%"
echo [ERREUR] Python introuvable. Installez Python 3.9+ et cochez "Add to PATH".
goto FIN_ERREUR
:PY_OK
echo Python : %PY% >> "%LOG%"
echo Python detecte : %PY%

set /p VERSION="Numero de version (ex: 9.5) : "
if "%VERSION%"=="" ( echo Version vide >> "%LOG%" & echo Erreur : version vide. & goto FIN_ERREUR )
echo Version : %VERSION% >> "%LOG%"

set /p DESC="Description des changements : "
if "%DESC%"=="" set DESC=Mise a jour v%VERSION%
echo Description : %DESC% >> "%LOG%"

echo.
echo --- Etape 1/6 : Mise a jour des fichiers de version ---
echo [ETAPE 1] maj_versions.py %VERSION% >> "%LOG%"
%PY% maj_versions.py %VERSION% >> "%LOG%" 2>&1
if errorlevel 1 ( echo [ERREUR] Etape 1 echouee. Voir %LOG% & goto FIN_ERREUR )
echo OK

echo.
echo --- Etape 2/6 : Generation setup.iss ---
echo [ETAPE 2] generer_setup_iss.py >> "%LOG%"
%PY% generer_setup_iss.py %VERSION% >> "%LOG%" 2>&1
if errorlevel 1 ( echo [ERREUR] Etape 2 echouee. Voir %LOG% & goto FIN_ERREUR )
echo OK

echo.
echo --- Etape 3/6 : Compilation PyInstaller ---
echo [ETAPE 3] PyInstaller >> "%LOG%"
%PY% -m PyInstaller PortailLREGE.spec --noconfirm >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [ERREUR] Etape 3 - PyInstaller a echoue. >> "%LOG%"
    echo [ERREUR] PyInstaller a echoue.
    echo Verifiez : %PY% -m pip install pyinstaller
    echo Log complet : %LOG%
    goto FIN_ERREUR
)
echo OK

echo.
echo --- Etape 4/6 : Compilation Inno Setup ---
echo [ETAPE 4] Inno Setup >> "%LOG%"
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo [ERREUR] Inno Setup 6 introuvable >> "%LOG%"
    echo [ERREUR] Inno Setup 6 introuvable.
    echo Telechargez : https://jrsoftware.org/isdl.php
    goto FIN_ERREUR
)
"%ISCC%" setup.iss >> "%LOG%" 2>&1
if errorlevel 1 ( echo [ERREUR] Etape 4 - Inno Setup echoue >> "%LOG%" & echo [ERREUR] Inno Setup a echoue. & goto FIN_ERREUR )
echo OK

set "EXE=dist\PortailLREGE_Setup_v%VERSION%.exe"
if not exist "%EXE%" (
    echo [ERREUR] Fichier %EXE% introuvable >> "%LOG%"
    echo [ERREUR] Fichier %EXE% introuvable apres compilation.
    goto FIN_ERREUR
)
echo EXE : %EXE% >> "%LOG%"

echo.
echo --- Etape 5/6 : Sauvegarde GitHub ---
echo [ETAPE 5] git add + commit + push >> "%LOG%"
git add portail.py version.json setup.iss maj_versions.py generer_setup_iss.py >> "%LOG%" 2>&1
git add LANCER_PORTAIL.bat PUBLIER_MAJ.bat SAUVEGARDER.bat PortailLREGE.spec lanceur.py .gitignore >> "%LOG%" 2>&1
git add SelecGE/ SelecMaster/ SuiviGE/ SuiviMaster/ CalendrierLREGE/ EscriTools/ >> "%LOG%" 2>&1
git add crege_app/ routes/ services/ >> "%LOG%" 2>&1
git add -u >> "%LOG%" 2>&1
git commit -m "Portail v%VERSION% - %DESC%" >> "%LOG%" 2>&1
git push >> "%LOG%" 2>&1
if errorlevel 1 ( echo [ERREUR] Etape 5 - git push echoue >> "%LOG%" & echo [ERREUR] git push a echoue. & goto FIN_ERREUR )
echo OK

echo.
echo --- Etape 6/6 : Publication GitHub Release ---
echo [ETAPE 6] gh release create >> "%LOG%"
gh --version >nul 2>&1
if errorlevel 1 (
    echo gh CLI absent, tentative winget >> "%LOG%"
    echo [INFO] Installation de GitHub CLI via winget...
    winget install --id GitHub.cli -e --silent >> "%LOG%" 2>&1
    if errorlevel 1 (
        echo [ATTENTION] gh CLI non installe.
        echo Uploadez manuellement %EXE% sur :
        echo https://github.com/atrcrege-a11y/Portail-LREGE/releases/new
        goto FIN_OK
    )
    echo gh installe. Authentification :
    gh auth login
)
gh release create "v%VERSION%" "%EXE%" --title "Portail LREGE v%VERSION%" --notes "%DESC%" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [ERREUR] gh release create echoue >> "%LOG%"
    echo [ATTENTION] Release GitHub echouee.
    echo Uploadez manuellement %EXE% sur :
    echo https://github.com/atrcrege-a11y/Portail-LREGE/releases/new
    goto FIN_OK
)
echo OK >> "%LOG%"

:FIN_OK
echo.
echo ================================================
echo   MAJ v%VERSION% publiee avec succes !
echo ================================================
echo Log : %LOG%
pause
exit /b 0

:FIN_ERREUR
echo.
echo ================================================
echo   ECHEC — Consultez le log pour le detail :
echo   %LOG%
echo ================================================
pause
exit /b 1
