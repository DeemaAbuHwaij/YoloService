#!/bin/bash
set -e

echo "🧪 Checking Python and creating venv..."
sudo apt-get update
sudo apt-get install -y python3.12-venv

PROJECT_DIR="$(pwd)"
VENV_PATH="$PROJECT_DIR/venv"
SERVICE_FILE="yolo-dev.service"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
  echo "🔧 Creating virtual environment with python3.12..."
  /usr/bin/python3.12 -m venv "$VENV_PATH"
fi

# Ensure venv activation script exists
if [ ! -f "$VENV_PATH/bin/activate" ]; then
  echo "❌ Virtualenv activation script not found!"
  exit 1
fi

# Activate virtual environment and install requirements
echo "📦 Installing requirements..."
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# Copy systemd service
echo "🛠️ Installing $SERVICE_FILE..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/

# Restart systemd service
echo "🔄 Restarting YOLO dev service..."
sudo systemctl daemon-reload
sudo systemctl restart yolo-dev.service
sudo systemctl enable yolo-dev.service

# Check status
if systemctl is-active --quiet yolo-dev.service; then
  echo "✅ YOLO Dev service is running!"
else
  echo "❌ YOLO Dev service failed to start."
  sudo systemctl status yolo-dev.service --no-pager
  exit 1
fi
