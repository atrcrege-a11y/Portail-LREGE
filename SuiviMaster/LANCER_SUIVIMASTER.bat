@echo off
title SuiviMaster — LREGE Grand Est
cd /d "%~dp0"
echo Demarrage SuiviMaster...
start "" http://localhost:5005
python app.py
pause
