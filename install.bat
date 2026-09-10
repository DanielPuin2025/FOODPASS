@echo off
REM Script de instalación y ejecución para Windows

echo ========================================
echo    FoodPass - Instalación Windows
echo ========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado.
    echo Por favor instala Python 3.12 o superior desde python.org
    pause
    exit /b 1
)

echo [OK] Python encontrado
echo.

REM Crear entorno virtual
echo [1/5] Creando entorno virtual...
python -m venv .venv-foodpass

REM Activar entorno virtual
echo [2/5] Activando entorno virtual...
call .venv-foodpass\Scripts\activate.bat

REM Actualizar pip
echo [3/5] Actualizando pip...
python -m pip install --upgrade pip

REM Instalar dependencias
echo [4/5] Instalando dependencias...
pip install -r requirements.txt

REM Inicializar base de datos
echo [5/5] Inicializando base de datos...
python DATABASE\crear_bd.py

echo.
echo ========================================
echo    Instalacion completada!
echo ========================================
echo.
echo Para ejecutar la aplicacion:
echo   run.bat
echo.
pause
