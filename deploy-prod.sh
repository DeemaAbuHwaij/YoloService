#!/bin/bash

set -e

echo "Checking /tmp directory..."
ls -ld /tmp
df -h /



PROJECT_DIR="$(pwd)"  # Use current working directory
SERVICE_FILE="yolo-prod.service"
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
sudo systemctl restart yolo-prod.service
sudo systemctl enable yolo-prod.service

# Check if the service is running
if systemctl is-active --quiet yolo-prod.service; then
  echo "✅ YOLO service is running!"
else
  echo "❌ YOLO service failed to start."
  sudo systemctl status yolo-prod.service --no-pager
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

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable otelcol

# Restart the OpenTelemetry Collector service
echo "🔁 Restarting OpenTelemetry Collector..."
sudo systemctl restart otelcol