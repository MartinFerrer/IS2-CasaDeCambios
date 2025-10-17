#!/bin/bash

echo "========================================"
echo "  API EXTERNO SIMULADOR - INICIANDO"
echo "  Servicio Bancario Simulado"
echo "========================================"
echo ""

echo "Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 no encontrado. Por favor instala Python 3.7+"
    exit 1
fi

python3 --version

echo ""
echo "Verificando gestor de dependencias..."

# Verificar si uv está disponible
if command -v uv &> /dev/null; then
    echo "Usando UV para manejo de dependencias desde proyecto principal..."
    
    # Cambiar al directorio principal para usar pyproject.toml
    cd ..
    echo "Instalando/verificando dependencias con uv desde /app..."
    uv sync --project app
    
    echo ""
    echo "Iniciando servicio API externo con uv en puerto 5001..."
    echo "Presiona Ctrl+C para detener el servicio"
    echo ""
    uv run --project app python3 api_externo_simulador/main.py
else
    echo "UV no encontrado, usando pip tradicional..."
    
    # Verificar dependencias con pip
    if ! python3 -c "import flask" &> /dev/null; then
        if [[ -f "requirements.txt" ]]; then
            echo "Instalando dependencias con pip desde requirements.txt local..."
            pip3 install -r requirements.txt
        else
            echo "Instalando dependencias desde proyecto principal..."
            cd ..
            pip3 install -e app
            cd api_externo_simulador
        fi
    fi
    
    echo ""
    echo "Iniciando servicio API externo en puerto 5001..."
    echo "Presiona Ctrl+C para detener el servicio"
    echo ""
    python3 main.py
fi