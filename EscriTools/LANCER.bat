@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>&1 || (echo Python introuvable. & pause & exit /b 1)
if not exist .venv\Scripts\activate.bat (
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt -q
) else (
    call .venv\Scripts\activate.bat
)
start "" http://localhost:5002
python app.py
