@echo off
setlocal EnableDelayedExpansion
title SYNESC - Synthese Competitions Escrime

:: ================================================================
::  SYNESC - Synthese Competitions Escrime
::  Lanceur Windows - v1.0.0
:: ================================================================

set "APP_DIR=%~dp0"
set "APP_FILE=%APP_DIR%app.py"
set "VENV_DIR=%APP_DIR%.venv"
set "PORT=5000"
set "PYTHON_CMD="

echo.
echo  +------------------------------------------------------+
echo  ^|        SYNESC - Synthese Competitions Escrime                       ^|
echo  ^|        Ligue Regionale Grand Est d'Escrime           ^|
echo  ^|        v1.0.0                                        ^|
echo  +------------------------------------------------------+
echo.

:: ----------------------------------------------------------------
:: 1. Verifier la presence de app.py
:: ----------------------------------------------------------------
echo  [1/5] Verification des fichiers...

if not exist "%APP_FILE%" (
    echo.
    echo  [ERREUR] app.py introuvable.
    echo  Assurez-vous que Lancer_SYNESC.bat est dans le meme
    echo  dossier que app.py.
    echo.
    echo  Dossier actuel : %APP_DIR%
    echo.
    pause
    exit /b 1
)
echo        OK - app.py trouve

:: ----------------------------------------------------------------
:: 2. Trouver Python
:: ----------------------------------------------------------------
echo  [2/5] Recherche de Python...

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto PYTHON_FOUND
)

python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python3"
    goto PYTHON_FOUND
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py"
    goto PYTHON_FOUND
)

echo.
echo  [ERREUR] Python n'est pas installe ou pas dans le PATH.
echo.
echo  Telechargez Python sur : https://www.python.org/downloads/
echo  IMPORTANT : cochez "Add Python to PATH" pendant l'installation.
echo.
pause
exit /b 1

:PYTHON_FOUND
for /f "tokens=2" %%V in ('"%PYTHON_CMD%" --version 2^>^&1') do set "PYVER=%%V"
echo        OK - Python %PYVER% detecte ^(%PYTHON_CMD%^)

:: Verifier version >= 3.9
for /f "tokens=1,2 delims=." %%A in ("%PYVER%") do (
    set "PYMAJ=%%A"
    set "PYMIN=%%B"
)
if %PYMAJ% LSS 3 goto PYTHON_TOO_OLD
if %PYMAJ% EQU 3 if %PYMIN% LSS 9 goto PYTHON_TOO_OLD
goto PYTHON_OK

:PYTHON_TOO_OLD
echo.
echo  [ERREUR] Python %PYVER% est trop ancien. Version 3.9+ requise.
echo.
pause
exit /b 1

:PYTHON_OK

:: ----------------------------------------------------------------
:: 3. Environnement virtuel
:: ----------------------------------------------------------------
echo  [3/5] Verification de l'environnement virtuel...

if exist "%VENV_DIR%\Scripts\python.exe" (
    echo        OK - Environnement virtuel existant
    goto VENV_READY
)

echo        Creation de l'environnement virtuel ^(premiere fois^)...
"%PYTHON_CMD%" -m venv "%VENV_DIR%"
if %errorlevel% neq 0 (
    echo.
    echo  [ERREUR] Impossible de creer l'environnement virtuel.
    echo  Essayez en tant qu'administrateur.
    echo.
    pause
    exit /b 1
)
echo        OK - Environnement virtuel cree

:VENV_READY
set "VPYTHON=%VENV_DIR%\Scripts\python.exe"
set "VPIP=%VENV_DIR%\Scripts\pip.exe"

:: ----------------------------------------------------------------
:: 4. Dependances
:: ----------------------------------------------------------------
echo  [4/5] Verification des dependances...

set "NEED_INSTALL=0"

"%VPYTHON%" -c "import flask" >nul 2>&1
if %errorlevel% neq 0 set "NEED_INSTALL=1"

"%VPYTHON%" -c "import openpyxl" >nul 2>&1
if %errorlevel% neq 0 set "NEED_INSTALL=1"

"%VPYTHON%" -c "import pdfplumber" >nul 2>&1
if %errorlevel% neq 0 set "NEED_INSTALL=1"

"%VPYTHON%" -c "import requests" >nul 2>&1
if %errorlevel% neq 0 set "NEED_INSTALL=1"

"%VPYTHON%" -c "import reportlab" >nul 2>&1
if %errorlevel% neq 0 set "NEED_INSTALL=1"

if "%NEED_INSTALL%"=="0" (
    echo        OK - Toutes les dependances sont presentes
    goto DEPS_OK
)

echo        Installation en cours ^(flask, openpyxl, pdfplumber, requests, reportlab^)...
echo        Connexion internet requise - patientez...
echo.

if exist "%APP_DIR%requirements.txt" (
    "%VPIP%" install -r "%APP_DIR%requirements.txt" --quiet
) else (
    "%VPIP%" install flask openpyxl --quiet
)

if %errorlevel% neq 0 (
    echo.
    echo  [ERREUR] Echec de l'installation des dependances.
    echo  Verifiez votre connexion internet et relancez.
    echo.
    pause
    exit /b 1
)
echo        OK - Dependances installees

:DEPS_OK

:: ----------------------------------------------------------------
:: 5. Port disponible
:: ----------------------------------------------------------------
echo  [5/5] Verification du port %PORT%...

netstat -ano 2>nul | findstr ":%PORT%" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo  [ATTENTION] Le port %PORT% est deja occupe.
    echo.
    choice /C ON /N /M "  Ouvrir le navigateur sur l'instance existante ? [O/N] "
    if errorlevel 2 exit /b 0
    goto OPEN_BROWSER
)
echo        OK - Port %PORT% disponible

:: ----------------------------------------------------------------
:: Lancement Flask
:: ----------------------------------------------------------------
echo.
echo  +------------------------------------------------------+
echo  ^|  Serveur demarre sur http://localhost:%PORT%          ^|
echo  ^|  Laissez cette fenetre ouverte.                      ^|
echo  ^|  Fermez-la pour arreter l'application.               ^|
echo  +------------------------------------------------------+
echo.

start "" /B "%VPYTHON%" "%APP_FILE%"

:: Attente demarrage via Python (pas besoin de curl)
set "WAIT=0"
echo  Demarrage en cours...

:WAIT_LOOP
timeout /t 1 /nobreak >nul
set /a WAIT+=1

"%VPYTHON%" -c "import urllib.request; urllib.request.urlopen('http://localhost:%PORT%/')" >nul 2>&1
if %errorlevel% equ 0 goto SERVER_READY

if %WAIT% GEQ 20 (
    echo  ^[ATTENTION^] Demarrage lent - ouverture du navigateur quand meme.
    goto OPEN_BROWSER
)
echo    %WAIT%s...
goto WAIT_LOOP

:SERVER_READY
echo  OK - Serveur pret !

:OPEN_BROWSER
echo.
echo  Ouverture du navigateur...
start "" "http://localhost:%PORT%/"

echo.
echo  -------------------------------------------------------
echo  Application en cours d'execution.
echo  Appuyez sur une touche pour ARRETER le serveur.
echo  -------------------------------------------------------
echo.
pause >nul

:: ----------------------------------------------------------------
:: Arret propre
:: ----------------------------------------------------------------
echo.
echo  Arret du serveur...

for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%P >nul 2>&1
)

echo  Au revoir !
timeout /t 2 /nobreak >nul
exit /b 0
