@echo off
cd /d "C:\Users\ATRCR\OneDrive\Bureau\LREGE"

echo === Sauvegarde LREGE vers GitHub ===
echo.

:: Demander un message de commit
set /p MSG="Description des modifications : "

if "%MSG%"=="" set MSG="Sauvegarde automatique"

git add .
git commit -m "%MSG%"
git push

echo.
echo === Sauvegarde terminee ! ===
echo Visible sur : https://github.com/atrcrege-a11y/Portail-LREGE
pause
