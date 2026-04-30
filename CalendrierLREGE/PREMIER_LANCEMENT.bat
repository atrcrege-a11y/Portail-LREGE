@echo off
title Installation dependances Calendrier LREGE
cd /d "%~dp0"
echo Installation des dependances...
pip install flask pandas openpyxl reportlab icalendar
echo.
echo Installation terminee. Vous pouvez lancer LANCER_CALENDRIER.bat
pause
