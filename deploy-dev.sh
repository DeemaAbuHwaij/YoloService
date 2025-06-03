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

# === OpenTelemetry Collector Setup ===
echo "📡 Installing OpenTelemetry Collector..."
sudo apt-get update
sudo apt-get -y install wget
wget https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.127.0/otelcol_0.127.0_linux_amd64.deb
sudo dpkg -i otelcol_0.127.0_linux_amd64.deb

# Configure OpenTelemetry Collector
echo "📝 Configuring OpenTelemetry Collector..."
sudo tee /etc/otelcol/config.yaml > /dev/null <<EOF
receivers:
  hostmetrics:
    collection_interval: 15s
    scrapers:
      cpu:
      memory:
      disk:
      filesystem:
      load:
      network:
      processes:

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"

service:
  pipelines:
    metrics:
      receivers: [hostmetrics]
      exporters: [prometheus]
EOF

# Restart the OpenTelemetry Collector service
echo "🔁 Restarting OpenTelemetry Collector..."
sudo systemctl restart otelcol
