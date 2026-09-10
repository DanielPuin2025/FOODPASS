#!/bin/bash
# Script de ejecución rápida para Linux/macOS

if [ ! -d ".venv-foodpass" ]; then
    echo "❌ Entorno virtual no encontrado. Ejecuta primero: ./install.sh"
    exit 1
fi

echo "🚀 Iniciando FoodPass..."
source .venv-foodpass/bin/activate
python FRONTEND/frontend.py
