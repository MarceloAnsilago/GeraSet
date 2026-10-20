@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente .venv nao encontrado. Configure o ambiente Python do projeto.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" iniciar-servicos.py
pause
