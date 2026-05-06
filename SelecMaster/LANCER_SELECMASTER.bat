@echo off
title SelecMaster — LREGE Grand Est
cd /d "%~dp0"
echo Demarrage SelecMaster...
start "" http://localhost:5004
python app.py
pause
