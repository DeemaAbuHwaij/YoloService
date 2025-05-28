#!/bin/bash

set -e

echo "📦 Ensuring python3.12-venv is installed..."
sudo apt-get update
sudo apt-get install -y python3.12-venv

PROJECT_DIR="$(pwd)"
SERVICE_FILE="yolo-dev.service"
VENV_PATH="$PROJECT_DIR/venv"

# Explicit venv creation with python3.12
if [ ! -d "$VENV_PATH" ]; then
  echo "🔧 Creating virtual environment with python3.12..."
  /usr/bin/python3.12 -m venv "$VENV_PATH" || {
    echo "❌ Failed to create virtual environment"
    exit 1
  }
fi

# Verify venv exists
if [ ! -f "$VENV_PATH/bin/activate" ]; then
  echo "❌ Virtualenv creation failed or is incomplete at: $VENV_PATH"
  exit 1
fi

# Activate venv and install dependencies
echo "📦 Installing requirements..."
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# Copy dev service file
echo "🛠️ Installing $SERVICE_FILE..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/

# Reload and restart systemd
echo "🔄 Restarting YOLO dev service..."
sudo systemctl daemon-reload
sudo systemctl restart yolo-dev.service
sudo systemctl enable yolo-dev.service

# Final status check
if systemctl is-active --quiet yolo-dev.service; then
  echo "✅ YOLO Dev service is running!"
else
  echo "❌ YOLO Dev service failed to start."
  sudo systemctl status yolo-dev.service --no-pager
  exit 1
fi
