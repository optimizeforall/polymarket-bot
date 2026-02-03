#!/bin/bash
# Setup script to install and start the BTC logger as a systemd service

set -e

SERVICE_NAME="btc-logger"
SERVICE_FILE="btc-logger.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_PATH="$SCRIPT_DIR/$SERVICE_FILE"
SYSTEMD_DIR="/etc/systemd/system"
TARGET_SERVICE="$SYSTEMD_DIR/$SERVICE_NAME.service"

echo "Setting up BTC Logger service..."

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "This script needs to be run with sudo to install the systemd service."
    echo "Please run: sudo $0"
    exit 1
fi

# Copy service file to systemd directory
echo "Installing service file..."
cp "$SERVICE_PATH" "$TARGET_SERVICE"

# Reload systemd to recognize the new service
echo "Reloading systemd..."
systemctl daemon-reload

# Enable the service to start on boot
echo "Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME.service"

# Start the service
echo "Starting service..."
systemctl start "$SERVICE_NAME.service"

# Show status
echo ""
echo "Service installed and started!"
echo ""
echo "Useful commands:"
echo "  Check status:    sudo systemctl status $SERVICE_NAME"
echo "  View logs:       sudo journalctl -u $SERVICE_NAME -f"
echo "  Stop service:    sudo systemctl stop $SERVICE_NAME"
echo "  Start service:   sudo systemctl start $SERVICE_NAME"
echo "  Restart service: sudo systemctl restart $SERVICE_NAME"
echo "  Disable service: sudo systemctl disable $SERVICE_NAME"
echo ""
