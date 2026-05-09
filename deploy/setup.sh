#!/bin/bash
set -e

# ProxyMaze Watchtower -- One-Shot Azure VM Setup Script
# Run as root or with sudo on an Ubuntu 24.04 LTS VM

PROJECT_DIR="/opt/proxymaze"
DOMAIN="${1:-proxymaze.yourdomain.com}"

echo "=== ProxyMaze Deployment ==="
echo "Domain: $DOMAIN"
echo "Project dir: $PROJECT_DIR"

# 1. System update
echo "[1/6] Updating system..."
apt update && apt upgrade -y

# 2. Install system dependencies
echo "[2/6] Installing system dependencies..."
apt install -y python3 python3-venv python3-pip git curl nginx

# 3. Ensure project directory exists and set permissions
echo "[3/6] Setting up project directory..."
mkdir -p "$PROJECT_DIR"
chown -R www-data:www-data "$PROJECT_DIR"

# 4. Create Python virtual environment and install dependencies
echo "[4/6] Installing Python dependencies..."
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    cd "$PROJECT_DIR"
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
else
    echo "WARNING: requirements.txt not found at $PROJECT_DIR/requirements.txt"
    echo "Please copy your project files to $PROJECT_DIR and re-run."
    exit 1
fi

# 5. Install systemd service
echo "[5/6] Installing systemd service..."
cp "$PROJECT_DIR/deploy/proxymaze.service" /etc/systemd/system/proxymaze.service

if [ ! -f "/etc/systemd/system/proxymaze.service" ]; then
    echo "WARNING: systemd service file not found."
    echo "Creating proxymaze.service from inline definition..."
    cat > /etc/systemd/system/proxymaze.service << 'EOF'
[Unit]
Description=ProxyMaze Watchtower
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/proxymaze
ExecStart=/opt/proxymaze/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
fi

systemctl daemon-reload
systemctl enable proxymaze
systemctl start proxymaze || true

# 6. Configure Nginx
echo "[6/6] Configuring Nginx..."

# Replace placeholder domain in nginx config
sed "s/proxymaze.yourdomain.com/$DOMAIN/g" "$PROJECT_DIR/deploy/nginx.conf" > /etc/nginx/sites-available/proxymaze

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/proxymaze /etc/nginx/sites-enabled/proxymaze

nginx -t && systemctl restart nginx

# 7. Optional: Install Certbot for SSL (commented out; run manually after DNS is configured)
echo ""
echo "=== Setup complete ==="
echo ""
echo "Service status:"
systemctl status proxymaze --no-pager || true

echo ""
echo "Next steps:"
echo "  1. Create a DNS A record pointing $DOMAIN to this VM's public IP."
echo "  2. Run: sudo apt install -y certbot python3-certbot-nginx"
echo "  3. Run: sudo certbot --nginx -d $DOMAIN"
echo ""
echo "Health check (HTTP):    curl http://$DOMAIN/health"
echo "Health check (HTTPS):   curl https://$DOMAIN/health  (after certbot)"
