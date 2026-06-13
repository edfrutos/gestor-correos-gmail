#!/bin/zsh
# Script puente para el Servicio de macOS
PROJECT_DIR="/Volumes/ESSAGER/__01.-Proyectos/__Herramientas_Desktop/gestor-correos-gmail"
cd "$PROJECT_DIR"

# Iterar sobre los archivos seleccionados en Finder
for f in "$@"; do
    ./.venv/bin/python server.py --open "$f"
done
