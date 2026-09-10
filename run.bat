@echo off
REM Script de ejecución rápida para Windows

if not exist ".venv-foodpass\" (
    echo ERROR: Entorno virtual no encontrado.
    echo Ejecuta primero: install.bat
    pause
    exit /b 1
)

echo Iniciando FoodPass...
call .venv-foodpass\Scripts\activate.bat
python FRONTEND\frontend.py
