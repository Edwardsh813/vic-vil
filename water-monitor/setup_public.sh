#!/bin/bash
# Setup script for public access to Water Monitor

echo "=== Water Monitor Public Access Setup ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo bash setup_public.sh"
    exit 1
fi

# Install nginx
echo "[1/5] Installing nginx..."
apt-get update
apt-get install -y nginx apache2-utils

# Stop existing Flask server
echo "[2/5] Stopping existing server..."
pkill -f "python3 app.py" 2>/dev/null || true
lsof -ti:5000 | xargs kill -9 2>/dev/null || true

# Install systemd service
echo "[3/5] Setting up systemd service..."
cp /home/hunter/projects/vic-vil/water-monitor/water-monitor.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable water-monitor
systemctl start water-monitor

# Setup nginx
echo "[4/5] Configuring nginx..."
cp /home/hunter/projects/vic-vil/water-monitor/nginx-water-monitor.conf /etc/nginx/sites-available/water-monitor
ln -sf /etc/nginx/sites-available/water-monitor /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload nginx
nginx -t && systemctl reload nginx

# Setup basic auth
echo "[5/5] Setting up basic authentication..."
echo "Enter a password for the 'admin' user:"
htpasswd -c /etc/nginx/.htpasswd admin

# Enable auth in nginx config
sed -i 's/# auth_basic/auth_basic/g' /etc/nginx/sites-available/water-monitor
systemctl reload nginx

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Water Monitor is now accessible at: http://$(hostname -I | awk '{print $1}')"
echo "Login with username: admin"
echo ""
echo "To add SSL (recommended), run:"
echo "  sudo apt install certbot python3-certbot-nginx"
echo "  sudo certbot --nginx -d yourdomain.com"
echo ""
echo "Service commands:"
echo "  sudo systemctl status water-monitor"
echo "  sudo systemctl restart water-monitor"
echo "  sudo journalctl -u water-monitor -f"
