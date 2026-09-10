#!/bin/bash
# Script de instalación y ejecución para Linux/macOS

echo "🍽️  FoodPass - Instalación"
echo "=========================="

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado. Por favor instálalo primero."
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"

# Crear entorno virtual
echo "📦 Creando entorno virtual..."
python3 -m venv .venv-foodpass

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source .venv-foodpass/bin/activate

# Actualizar pip
echo "⬆️  Actualizando pip..."
pip install --upgrade pip

# Instalar dependencias
echo "📚 Instalando dependencias..."
pip install -r requirements.txt

# Inicializar base de datos
echo "🗄️  Inicializando base de datos..."
python DATABASE/crear_bd.py

echo ""
echo "✅ ¡Instalación completada!"
echo ""
echo "Para ejecutar la aplicación:"
echo "  source .venv-foodpass/bin/activate"
echo "  python FRONTEND/frontend.py"
echo ""
echo "O simplemente ejecuta: ./run.sh"
