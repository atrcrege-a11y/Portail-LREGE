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

:: ── Dependances SelecGE + SelecMaster (Python systeme) ──────
echo  [2/3] Installation dependances SelecGE + SelecMaster...
"%PYTHON_CMD%" -m pip install flask openpyxl pdfplumber requests beautifulsoup4 --quiet
if %errorlevel% neq 0 (
    echo  [ATTENTION] Erreur installation — verifiez la connexion internet
)

:: ── Dependances EscriTools (Python systeme) ────────────────
echo        Installation dependances EscriTools...
"%PYTHON_CMD%" -m pip install pdfplumber pillow --quiet

:: ── Dependances SYNESC (Python systeme, pas de venv) ────
echo  [3/3] Installation dependances SYNESC...
"%PYTHON_CMD%" -m pip install flask openpyxl pdfplumber requests reportlab --quiet
if %errorlevel% neq 0 (
    echo  [ATTENTION] Erreur installation SYNESC - verifiez la connexion internet
) else (
    echo        OK - Dependances SYNESC installees
)

echo.
echo  +------------------------------------------------------+
echo  ^|  Installation terminee !                            ^|
echo  ^|  Vous pouvez lancer LANCER_PORTAIL.bat              ^|
echo  +------------------------------------------------------+
echo.
pause
