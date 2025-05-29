#!/bin/bash

set -e

PROJECT_DIR="$(pwd)"
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

# Fix for pip temporary directory issue
echo "🛠️ Ensuring /tmp exists and is usable by current user..."
sudo mkdir -p /tmp
sudo chmod 1777 /tmp
export TMPDIR=/tmp

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

# Free up disk space before install
echo "🧹 Cleaning up disk space..."
sudo apt-get clean
sudo rm -rf /var/lib/apt/lists/*
sudo rm -rf /var/log/*.gz /var/log/*.1 /var/log/journal/*
sudo journalctl --vacuum-time=1d
sudo apt-get autoremove -y

# Check free space
FREE_MB=$(df / | awk 'NR==2 {print $4 / 1024}')
echo "📦 Free space available: ${FREE_MB} MB"
if (( $(echo "$FREE_MB < 500" | bc -l) )); then
  echo "❌ Not enough disk space (<500MB). Aborting otelcol install."
  df -h
  exit 1
fi

# Clean previous otelcol if it exists
echo "🧹 Cleaning previous otelcol install (if any)..."
sudo systemctl stop otelcol || true
sudo rm -f /usr/bin/otelcol
sudo rm -f /etc/systemd/system/otelcol.service
sudo rm -rf /etc/otelcol

# Download and install otelcol
sudo apt-get update
sudo apt-get -y install wget
wget -O otelcol.deb https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.127.0/otelcol_0.127.0_linux_amd64.deb
sudo dpkg -i otelcol.deb

# Configure OpenTelemetry Collector
echo "📝 Configuring OpenTelemetry Collector..."
sudo mkdir -p /etc/otelcol
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

# Reload and restart otelcol
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable otelcol
echo "🔁 Restarting OpenTelemetry Collector..."
sudo systemctl restart otelcol

# Final check
if systemctl is-active --quiet otelcol; then
  echo "✅ OpenTelemetry Collector is running!"
else
  echo "❌ otelcol failed to start."
  sudo systemctl status otelcol --no-pager
  exit 1
fi
