#!/bin/bash

set -e

echo "🧪 Ensuring python3-venv is installed..."
sudo apt-get update
sudo apt-get install -y python3-venv

PROJECT_DIR="$(pwd)"
SERVICE_FILE="yolo-dev.service"
VENV_PATH="$PROJECT_DIR/venv"

# Create venv if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
  echo "🔧 Creating virtual environment..."
  python3 -m venv "$VENV_PATH"
fi

# Show contents of venv/bin to verify
echo "📁 Contents of $VENV_PATH/bin:"
ls -la "$VENV_PATH/bin"

# Check activation script
if [ ! -f "$VENV_PATH/bin/activate" ]; then
  echo "❌ Virtualenv activation script not found at $VENV_PATH/bin/activate"
  exit 1
fi

# Activate and install
echo "📦 Installing requirements..."
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# Copy and reload service
echo "🛠️ Copying $SERVICE_FILE to systemd..."
sudo cp "$PROJECT_DIR/$SERVICE_FILE" /etc/systemd/system/
echo "🔄 Reloading and restarting service..."
sudo systemctl daemon-reload
sudo systemctl restart yolo-dev.service
sudo systemctl enable yolo-dev.service

# Final check
if systemctl is-active --quiet yolo-dev.service; then
  echo "✅ YOLO Dev service is running!"
else
  echo "❌ YOLO Dev service failed to start."
  sudo systemctl status yolo-dev.service --no-pager
  exit 1
fi
