#!/bin/bash

set -e

PROJECT_DIR="/home/deema/PycharmProjects/YoloService"
SERVICE_FILE="yolo.service"
VENV_PATH="$PROJECT_DIR/venv"

# Create venv if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
  echo "🔧 Creating virtual environment..."
  python3 -m venv "$VENV_PATH"
fi

# Activate venv and install dependencies
echo "📦 Installing requirements..."
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# Copy systemd service file
echo "🛠️ Copying $SERVICE_FILE to systemd..."
sudo cp "$PROJECT_DIR/$SERVICE_FILE" /etc/systemd/system/

# Reload and restart systemd service
echo "🔄 Reloading and restarting YOLO service..."
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl restart yolo.service
sudo systemctl enable yolo.service

# Check if the service is running
if systemctl is-active --quiet yolo.service; then
  echo "✅ YOLO service is running!"
else
  echo "❌ YOLO service failed to start."
  sudo systemctl status yolo.service --no-pager
  exit 1
fi
