@echo off
cd /d "C:\Users\ATRCR\OneDrive\Bureau\LREGE"

echo === Initialisation du depot Git LREGE ===

:: Creer le .gitignore
(
echo # Python
echo __pycache__/
echo *.py[cod]
echo *.pyo
echo .env
echo venv/
echo .venv/
echo
echo # Fichiers temporaires
echo tmp*/
echo *.tmp
echo *.log
echo
echo # Fichiers generes
echo dist/
echo build/
echo *.spec
echo
echo # Config locale
echo config_selection.json
echo
echo # OS
echo .DS_Store
echo Thumbs.db
echo desktop.ini
echo
echo # Fichiers Excel generes
echo sorties/
echo output/
) > .gitignore

:: Initialiser Git
git init
git branch -M main

:: Ajouter le remote GitHub
git remote add origin https://github.com/atrcrege-a11y/Portail-LREGE.git

:: Premier commit
git add .
git commit -m "Initial commit - Portail LREGE (SelecGE + SYNESC + EscriTools)"

:: Pousser vers GitHub
git push -u origin main

echo.
echo === Termine ! Verifie sur github.com/atrcrege-a11y/Portail-LREGE ===
pause
