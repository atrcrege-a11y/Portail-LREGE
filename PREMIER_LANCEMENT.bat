@echo off
title Portail LREGE — Installation des dependances
cd /d "%~dp0"

echo.
echo  +------------------------------------------------------+
echo  ^|  Portail LREGE — Premier lancement                  ^|
echo  ^|  Installation des dependances                        ^|
echo  +------------------------------------------------------+
echo.

:: ── Trouver Python ──────────────────────────────────────────
set "PYTHON_CMD="
python --version >nul 2>&1 && set "PYTHON_CMD=python" && goto PYTHON_OK
python3 --version >nul 2>&1 && set "PYTHON_CMD=python3" && goto PYTHON_OK
py --version >nul 2>&1 && set "PYTHON_CMD=py" && goto PYTHON_OK

echo  [ERREUR] Python introuvable. Installez Python 3.9+
echo  https://www.python.org/downloads/
echo  IMPORTANT : cochez "Add Python to PATH"
pause
exit /b 1

:PYTHON_OK
echo  [1/3] Python detecte : %PYTHON_CMD%

:: ── Dependances SelecGE (Python systeme) ───────────────────
echo  [2/3] Installation dependances SelecGE...
"%PYTHON_CMD%" -m pip install flask openpyxl pdfplumber requests --quiet
if %errorlevel% neq 0 (
    echo  [ATTENTION] Erreur installation SelecGE — verifiez la connexion internet
)

:: ── Dependances EscriTools (Python systeme) ────────────────
echo        Installation dependances EscriTools...
"%PYTHON_CMD%" -m pip install pdfplumber pillow --quiet

:: ── Venv SYNESC ─────────────────────────────────────────────
echo  [3/3] Creation environnement SYNESC...
if not exist "%~dp0SYNESC\.venv\Scripts\python.exe" (
    "%PYTHON_CMD%" -m venv "%~dp0SYNESC\.venv"
    "%~dp0SYNESC\.venv\Scripts\pip.exe" install flask openpyxl pdfplumber requests reportlab --quiet
    echo        OK - Environnement SYNESC cree
) else (
    echo        OK - Environnement SYNESC deja present
)

echo.
echo  +------------------------------------------------------+
echo  ^|  Installation terminee !                            ^|
echo  ^|  Vous pouvez lancer LANCER_PORTAIL.bat              ^|
echo  +------------------------------------------------------+
echo.
pause
