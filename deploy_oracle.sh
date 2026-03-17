#!/bin/bash
# ==============================================================================
# Oracle VM Deployment Script for Data Center AI Site Selector
# Domain: dataselection.cloud
# Target OS: Ubuntu 22.04 LTS or 24.04 LTS on Oracle Cloud (OCI)
# ==============================================================================

set -e

DOMAIN="dataselection.cloud"
REPO_DIR="/home/ubuntu/site-selector"
PORT="8505"

echo "🚀 [1/6] Updating system and installing dependencies..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx tmux sqlite3

echo "⚙️ [2/6] Configuring Oracle Cloud Internal Firewall (iptables)..."
# Oracle VMs have strict default iptables. We need to allow HTTP (80) and HTTPS (443)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
# Also opening 8505 just in case we need direct access for debugging
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport $PORT -j ACCEPT
sudo netfilter-persistent save || true
echo "ℹ️  Remember to also open Port 80 and 443 in your Oracle Cloud VCN Security List!"

echo "📦 [3/6] Setting up project directory and Python environment..."
# Check if repo exists, if not create dir structure
if [ ! -d "$REPO_DIR" ]; then
    echo "Creating directory $REPO_DIR..."
    mkdir -p "$REPO_DIR"
    echo "Please ensure you have uploaded your code into $REPO_DIR before running this setup."
    exit 1
fi

cd "$REPO_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "🔄 [4/6] Creating Systemd Service for Streamlit app..."
cat <<EOF | sudo tee /etc/systemd/system/siteai.service
[Unit]
Description=Site Selection AI Streamlit App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=$REPO_DIR
Environment="PATH=$REPO_DIR/venv/bin"
# Run headless locally on port 8505. Nginx will forward requests to it.
ExecStart=$REPO_DIR/venv/bin/streamlit run frontend_ui/app.py --server.port $PORT --server.address 127.0.0.1 --server.headless true
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable siteai
sudo systemctl restart siteai

echo "🌐 [5/6] Configuring Nginx Reverse Proxy for $DOMAIN..."
cat <<EOF | sudo tee /etc/nginx/sites-available/siteai
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Streamlit specific websocket config required
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/siteai /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "🔒 [6/6] Requesting Let's Encrypt SSL Certificate..."
echo "Certbot will now attempt to get an SSL cert for $DOMAIN."
echo "CRITICAL: Ensure your domain's DNS A Record points to this Oracle VM's public IP before proceeding!"

# Try non-interactive first, but don't fail script if it fails (user might need to configure DNS first)
sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --register-unsafely-without-email || \
echo "⚠️ Certbot failed. This Usually means your DNS 'A' record (dataselection.cloud pointing to your VM IP) hasn't propagated yet. Please configure GoDaddy DNS, wait 5 minutes, and then run: 
sudo certbot --nginx -d dataselection.cloud -d www.dataselection.cloud"

echo "=============================================================================="
echo "✅ Backend Deployment script finished! Check status with: sudo systemctl status siteai"
echo "=============================================================================="
