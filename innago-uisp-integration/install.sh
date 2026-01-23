#!/bin/bash
# Victorian Village Integration - Install Script
# Run as root on the target VM

set -e

APP_DIR="/opt/vic-vil-integration"
SERVICE_USER="vicvil"

echo "=== Victorian Village Integration Installer ==="

# Create service user
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "Creating service user: $SERVICE_USER"
    useradd -r -s /bin/false "$SERVICE_USER"
fi

# Create app directory
echo "Setting up $APP_DIR"
mkdir -p "$APP_DIR"

# Copy files (assumes running from project directory)
cp -r src main.py requirements.txt config.example.yaml "$APP_DIR/"

# Set up Python venv
echo "Creating Python virtual environment"
cd "$APP_DIR"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# Set ownership
chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"

# Install systemd service
echo "Installing systemd service"
cp vic-vil-sync.service /etc/systemd/system/ 2>/dev/null || \
    cp /opt/vic-vil-integration/../vic-vil-sync.service /etc/systemd/system/ 2>/dev/null || \
    echo "Note: Copy vic-vil-sync.service to /etc/systemd/system/ manually"

systemctl daemon-reload

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Copy config.example.yaml to config.yaml:"
echo "   cp $APP_DIR/config.example.yaml $APP_DIR/config.yaml"
echo ""
echo "2. Edit config.yaml with your API keys:"
echo "   nano $APP_DIR/config.yaml"
echo ""
echo "3. Test the sync manually:"
echo "   cd $APP_DIR && sudo -u $SERVICE_USER ./venv/bin/python main.py --once"
echo ""
echo "4. Start the service:"
echo "   systemctl enable vic-vil-sync"
echo "   systemctl start vic-vil-sync"
echo ""
echo "5. Check logs:"
echo "   journalctl -u vic-vil-sync -f"
