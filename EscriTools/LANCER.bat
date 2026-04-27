@echo off
title EscriTools

python --version >nul 2>&1
if errorlevel 1 (
    echo Python n'est pas installe.
    echo Telechargez-le sur https://python.org
    pause
    exit /b 1
)

python -c "import pdfplumber" >nul 2>&1
if errorlevel 1 (
    echo Installation de pdfplumber...
    python -m pip install pdfplumber --quiet
)

python -c "import reportlab" >nul 2>&1
if errorlevel 1 (
    echo Installation de reportlab...
    python -m pip install reportlab --quiet
)

python escritools.py
