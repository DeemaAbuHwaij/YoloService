#!/bin/bash

set -e  # Exit on any error

# Set project directory to current directory
PROJECT_DIR="$(pwd)"
SERVICE_FILE="yolo-dev.service"
VENV_PATH="$PROJECT_DIR/venv"

echo "📂 Current directory: $PROJECT_DIR"
echo "📁 Virtual environment path: $VENV_PATH"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
  echo "🔧 Creating virtual environment..."
  python3 -m venv "$VENV_PATH"
fi

# Activate virtual environment and install requirements
echo "📦 Installing requirements..."
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# Copy the systemd service file
echo "🛠️ Copying $SERVICE_FILE to systemd..."
sudo cp "$PROJECT_DIR/$SERVICE_FILE" /etc/systemd/system/

# Reload and restart systemd service
echo "🔄 Reloading and restarting YOLO service..."
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl restart yolo-dev.service
sudo systemctl enable yolo-dev.service

# Check if the service is running
if systemctl is-active --quiet yolo-dev.service; then
  echo "✅ YOLO service is running."
else
  echo "❌ YOLO service failed to start."
  journalctl -u yolo-dev.service --no-pager -n 20
  exit 1
fi
