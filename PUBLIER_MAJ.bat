@echo off
cd /d "%~dp0"

echo ================================================
echo   Publication MAJ Portail LREGE
echo ================================================
echo.

:: ── Detecter Python ──────────────────────────────────────────
set "PY="
python --version >nul 2>&1 && set "PY=python" && goto PY_OK
py --version >nul 2>&1 && set "PY=py" && goto PY_OK
python3 --version >nul 2>&1 && set "PY=python3" && goto PY_OK
echo [ERREUR] Python introuvable. Installez Python 3.9+ et cochez "Add to PATH".
pause & exit /b 1
:PY_OK
echo Python detecte : %PY%

set /p VERSION="Numero de version (ex: 1.3.0) : "
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
echo --- Etape 3/6 : Compilation Inno Setup ---

set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe

if "%ISCC%"=="" (
    echo Inno Setup non trouve. Lance le manuellement puis appuie sur une touche.
    pause
) else (
    "%ISCC%" setup.iss
    if errorlevel 1 ( echo Erreur compilation. & pause & exit /b 1 )
    echo OK
)

set EXE=dist\PortailLREGE_Setup_v%VERSION%.exe
if not exist "%EXE%" ( echo Fichier %EXE% introuvable. & pause & exit /b 1 )

echo.
echo --- Etape 4/6 : Sauvegarde GitHub ---
git config gc.auto 0
git add .
git commit -m "Portail v%VERSION% - %DESC%"
git push
if errorlevel 1 ( echo Erreur git push. & pause & exit /b 1 )
echo OK

echo.
echo --- Etape 5/6 : Publication GitHub Release ---
gh release create "v%VERSION%" "%EXE%" --title "Portail LREGE v%VERSION%" --notes "%DESC%"
if errorlevel 1 ( echo Erreur GitHub Release. & pause & exit /b 1 )
echo OK

echo.
echo ================================================
echo   MAJ v%VERSION% publiee avec succes !
echo ================================================
pause
