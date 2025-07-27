#!/bin/bash

# Nombre del ejecutable generado por PyInstaller
APP_NAME="contador_tareas_semanal"
DIST_DIR="dist"
DEST_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

# Crear carpeta destino si no existe
mkdir -p "$DEST_DIR"
mkdir -p "$DESKTOP_DIR"

# Copiar ejecutable
cp "$DIST_DIR/$APP_NAME" "$DEST_DIR/"

# Crear lanzador .desktop
cat > "$DESKTOP_DIR/$APP_NAME.desktop" <<EOL
[Desktop Entry]
Name=Contador de Tareas Semanales
Exec=$DEST_DIR/$APP_NAME
Icon=utilities-terminal
Type=Application
Categories=Utility;
EOL

chmod +x "$DEST_DIR/$APP_NAME"
chmod +x "$DESKTOP_DIR/$APP_NAME.desktop"

echo "Instalación completada. Puedes buscar 'Contador de Tareas Semanales' en tu menú de aplicaciones."
