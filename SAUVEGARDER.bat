@echo off
cd /d "%~dp0"

echo === Sauvegarde LREGE vers GitHub ===
echo.

:: ── Supprimer le verrou git si présent (crash précédent) ──────
if exist ".git\index.lock" (
    echo [INFO] Suppression du verrou git stale...
    del /f ".git\index.lock"
)
if exist ".git\refs\heads\*.lock" (
    del /f ".git\refs\heads\*.lock"
)

:: Demander un message de commit
set /p MSG="Description des modifications : "
if "%MSG%"=="" set MSG=Sauvegarde automatique

:: ── N'ajouter que les fichiers sources (pas .venv, build, etc.) ──
git add portail.py version.json setup.iss maj_versions.py generer_setup_iss.py
git add LANCER_PORTAIL.bat PREMIER_LANCEMENT.bat PUBLIER_MAJ.bat SAUVEGARDER.bat
git add PortailLREGE.spec lanceur.py .gitignore 2>nul
git add SelecGE\ SelecMaster\ SuiviGE\ SuiviMaster\ CalendrierLREGE\ EscriTools\
git add crege_app\ routes\ services\ SYNESC\app.py SYNESC\core\ SYNESC\competitions\
git add -u

git commit -m "%MSG%"
if errorlevel 1 (
    echo [INFO] Rien de nouveau a commiter.
    goto PUSH
)

:PUSH
git push
if errorlevel 1 (
    echo [ERREUR] git push a echoue. Verifiez la connexion et les droits.
    pause & exit /b 1
)

echo.
echo === Sauvegarde terminee ! ===
echo Visible sur : https://github.com/atrcrege-a11y/Portail-LREGE
pause
