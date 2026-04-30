@echo off
title Calendrier LREGE — port 5003
cd /d "%~dp0"
echo Demarrage Calendrier LREGE (port 5003)...
start "" http://localhost:5003
python app.py
pause
