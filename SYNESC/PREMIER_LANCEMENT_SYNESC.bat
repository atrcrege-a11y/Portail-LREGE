@echo off
title SYNESC - Installation des dependances
cd /d "%~dp0"

echo.
echo  +------------------------------------------------------+
echo  ^|  SYNESC - Premier lancement                          ^|
echo  ^|  Installation des dependances                        ^|
echo  +------------------------------------------------------+
echo.

:: -- Trouver Python -------------------------------------------
set "PYTHON_CMD="
python --version >nul 2>&1 && set "PYTHON_CMD=python" && goto PYTHON_OK
python3 --version >nul 2>&1 && set "PYTHON_CMD=python3" && goto PYTHON_OK
py --version >nul 2>&1 && set "PYTHON_CMD=py" && goto PYTHON_OK

echo  [ERREUR] Python introuvable. Installez Python 3.9 ou plus recent :
echo  https://www.python.org/downloads/
echo  IMPORTANT : cochez "Add Python to PATH" pendant l'installation.
echo.
pause
exit /b 1

:PYTHON_OK
echo  [1/2] Python detecte : %PYTHON_CMD%

echo  [2/2] Installation des dependances (connexion internet requise)...
"%PYTHON_CMD%" -m pip install -r "%~dp0requirements.txt" --quiet --no-warn-script-location
if %errorlevel% neq 0 (
    echo.
    echo  [ERREUR] Echec de l'installation. Verifiez la connexion internet
    echo  puis relancez ce fichier.
    echo.
    pause
    exit /b 1
)

echo        OK - Dependances installees
echo.
echo  +------------------------------------------------------+
echo  ^|  Installation terminee.                              ^|
echo  ^|  Lancez SYNESC depuis le raccourci du Bureau.        ^|
echo  +------------------------------------------------------+
echo.
pause
