#!/bin/bash

set -e


sudo apt-get update
sudo apt-get install -y python3.12-venv

PROJECT_DIR="$(pwd)"
SERVICE_FILE="yolo-dev.service"
VENV_PATH="$PROJECT_DIR/venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
  echo "🔧 Creating virtual environment with python3.12..."
  /usr/bin/python3.12 -m venv "$VENV_PATH" || {
    echo "❌ Failed to create virtual environment"
    exit 1
  }
fi

# Activate virtual environment and install dependencies
echo "📦 Installing requirements..."
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# Copy systemd service file
echo "🛠️ Installing $SERVICE_FILE..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/

# Reload and restart systemd service
echo "🔄 Restarting YOLO dev service..."
sudo systemctl daemon-reload
sudo systemctl restart yolo-dev.service
sudo systemctl enable yolo-dev.service

# Check if the service is running
if systemctl is-active --quiet yolo-dev.service; then
  echo "✅ YOLO Dev service is running!"
else
  echo "❌ YOLO Dev service failed to start."
  sudo systemctl status yolo-dev.service --no-pager
  exit 1
fi
