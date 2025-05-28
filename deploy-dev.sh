#!/bin/bash

set -e

PROJECT_DIR="$(pwd)"
SERVICE_FILE="yolo-dev.service"
VENV_PATH="$PROJECT_DIR/venv"

# Create venv if not exists
if [ ! -d "$VENV_PATH" ]; then
  echo "🔧 Creating virtual environment..."
  python3 -m venv "$VENV_PATH"
fi

# Activate venv and install dependencies
echo "📦 Installing requirements..."
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# Copy dev service file
echo "🛠️ Installing $SERVICE_FILE..."
sudo cp "$PROJECT_DIR/$SERVICE_FILE" /etc/systemd/system/

# Reload and restart systemd
echo "🔄 Restarting YOLO dev service..."
sudo systemctl daemon-reload
sudo systemctl restart yolo-dev.service
sudo systemctl enable yolo-dev.service

# Check service status
if systemctl is-active --quiet yolo-dev.service; then
  echo "✅ YOLO Dev service is running!"
else
  echo "❌ YOLO Dev service failed."
  sudo systemctl status yolo-dev.service --no-pager
  exit 1
fi
