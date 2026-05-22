@echo off
title SuiviGE — LREGE Grand Est
cd /d "%~dp0"
echo Demarrage SuiviGE...
start "" http://localhost:5006
python app.py
pause
