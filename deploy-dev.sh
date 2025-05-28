#!/bin/bash
set -e

echo "🔍 Checking Python 3.12 and creating virtual environment..."

# Ensure venv module is available
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv

PROJECT_DIR="$(pwd)"
VENV_PATH="$PROJECT_DIR/venv"
SERVICE_FILE="yolo-dev.service"

# Check Python location
echo "📍 Python version:"
/usr/bin/python3.12 --version || which python3.12

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
  echo "🔧 Creating virtual environment..."
  /usr/bin/python3.12 -m venv "$VENV_PATH"
fi

# Check if venv was created successfully
if [ ! -f "$VENV_PATH/bin/activate" ]; then
  echo "❌ Virtualenv activation script not found at $VENV_PATH/bin/activate"
  ls -l "$VENV_PATH" || echo "⚠️ No venv folder found!"
  exit 1
fi

# Activate venv and install requirements
echo "📦 Installing requirements..."
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# Install systemd service
echo "🛠️ Installing $SERVICE_FILE..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/

# Restart service
echo "🔄 Restarting YOLO dev service..."
sudo systemctl daemon-reload
sudo systemctl restart yolo-dev.service
sudo systemctl enable yolo-dev.service

# Confirm service status
if systemctl is-active --quiet yolo-dev.service; then
  echo "✅ YOLO Dev service is running!"
else
  echo "❌ YOLO Dev service failed to start."
  sudo systemctl status yolo-dev.service --no-pager
  exit 1
fi
