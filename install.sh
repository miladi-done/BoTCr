#!/bin/bash

# Master Bot Installation Script
# نصب خودکار ربات مادر و تمام وابستگی‌ها

set -e

echo "🎯 شروع نصب ربات مادر - سازنده ربات‌های فروش VPN"
echo "=================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ لطفا این اسکریپت را با دسترسی root اجرا کنید (sudo)"
    exit 1
fi

# Update system
echo "📦 بروزرسانی سیستم..."
apt update && apt upgrade -y

# Install required packages
echo "📋 نصب پکیج‌های مورد نیاز..."
apt install -y python3 python3-pip python3-venv git curl wget unzip systemd nginx sqlite3 htop

# Install Docker (optional for advanced deployment)
echo "🐳 نصب Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl enable docker
systemctl start docker

# Create master bot user
echo "👤 ایجاد کاربر master-bot..."
if ! id "master-bot" &>/dev/null; then
    useradd -m -s /bin/bash master-bot
    usermod -aG docker master-bot
fi

# Create directories
echo "📁 ایجاد دایرکتوری‌ها..."
mkdir -p /opt/master-bot
mkdir -p /workspace/generated_bots
mkdir -p /var/log/master-bot

# Set permissions
chown -R master-bot:master-bot /opt/master-bot
chown -R master-bot:master-bot /workspace/generated_bots
chown -R master-bot:master-bot /var/log/master-bot

# Copy files to installation directory
echo "📋 کپی فایل‌ها..."
cp master_bot.py /opt/master-bot/
cp web_panel.py /opt/master-bot/
cp VPNBot /opt/master-bot/
cp -r templates /opt/master-bot/ 2>/dev/null || true

# Create Python virtual environment
echo "🐍 ایجاد محیط مجازی Python..."
cd /opt/master-bot
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 نصب وابستگی‌های Python..."
pip install --upgrade pip
pip install python-telegram-bot==20.7 requests psutil flask werkzeug sqlite3

# Create configuration file
echo "⚙️ ایجاد فایل تنظیمات..."
cat > /opt/master-bot/config.py << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Master Bot Configuration
MASTER_BOT_TOKEN = "YOUR_MASTER_BOT_TOKEN_HERE"
ADMIN_ID = 0  # Your Telegram ID

# Web Panel Configuration
WEB_SECRET_KEY = "change-this-secret-key-in-production"
WEB_PORT = 5000
WEB_HOST = "0.0.0.0"

# Database Configuration
DB_NAME = "master_bot.db"
BOTS_DIR = "/workspace/generated_bots"

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FILE = "/var/log/master-bot/master-bot.log"
EOF

# Create systemd service for master bot
echo "🔧 ایجاد سرویس systemd برای ربات مادر..."
cat > /etc/systemd/system/master-bot.service << 'EOF'
[Unit]
Description=Master Bot - VPN Sales Bot Generator
After=network.target

[Service]
Type=simple
User=master-bot
Group=master-bot
WorkingDirectory=/opt/master-bot
Environment=PYTHONPATH=/opt/master-bot
ExecStart=/opt/master-bot/venv/bin/python master_bot.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/master-bot/master-bot.log
StandardError=append:/var/log/master-bot/master-bot.log

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for web panel
echo "🌐 ایجاد سرویس systemd برای پنل وب..."
cat > /etc/systemd/system/master-bot-web.service << 'EOF'
[Unit]
Description=Master Bot Web Panel
After=network.target

[Service]
Type=simple
User=master-bot
Group=master-bot
WorkingDirectory=/opt/master-bot
Environment=PYTHONPATH=/opt/master-bot
ExecStart=/opt/master-bot/venv/bin/python web_panel.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/master-bot/web-panel.log
StandardError=append:/var/log/master-bot/web-panel.log

[Install]
WantedBy=multi-user.target
EOF

# Configure nginx for web panel
echo "🌐 تنظیم Nginx برای پنل وب..."
cat > /etc/nginx/sites-available/master-bot << 'EOF'
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
}
EOF

# Enable nginx site
ln -sf /etc/nginx/sites-available/master-bot /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

# Create startup script
echo "🚀 ایجاد اسکریپت راه‌اندازی..."
cat > /opt/master-bot/start.sh << 'EOF'
#!/bin/bash

echo "🎯 راه‌اندازی ربات مادر..."

# Start services
systemctl daemon-reload
systemctl enable master-bot
systemctl enable master-bot-web
systemctl enable nginx

systemctl start master-bot
systemctl start master-bot-web
systemctl start nginx

echo "✅ ربات مادر با موفقیت راه‌اندازی شد!"
echo "🌐 پنل وب: http://$(hostname -I | awk '{print $1}')"
echo "👤 نام کاربری پنل: admin"
echo "🔑 رمز عبور پنل: admin123"
echo ""
echo "⚠️ نکات مهم:"
echo "1. توکن ربات مادر را در فایل /opt/master-bot/config.py تنظیم کنید"
echo "2. آیدی عددی خود را در همان فایل وارد کنید"
echo "3. رمز عبور پنل وب را تغییر دهید"
echo "4. برای مشاهده لاگ‌ها: journalctl -u master-bot -f"
EOF

chmod +x /opt/master-bot/start.sh

# Create stop script
cat > /opt/master-bot/stop.sh << 'EOF'
#!/bin/bash

echo "⏹️ متوقف کردن ربات مادر..."

systemctl stop master-bot
systemctl stop master-bot-web

echo "✅ ربات مادر متوقف شد!"
EOF

chmod +x /opt/master-bot/stop.sh

# Create update script
cat > /opt/master-bot/update.sh << 'EOF'
#!/bin/bash

echo "🔄 بروزرسانی ربات مادر..."

# Stop services
systemctl stop master-bot
systemctl stop master-bot-web

# Update code (if using git)
cd /opt/master-bot
git pull 2>/dev/null || echo "Git repository not found"

# Update dependencies
source venv/bin/activate
pip install --upgrade python-telegram-bot requests psutil flask werkzeug

# Restart services
systemctl start master-bot
systemctl start master-bot-web

echo "✅ بروزرسانی کامل شد!"
EOF

chmod +x /opt/master-bot/update.sh

# Create backup script
cat > /opt/master-bot/backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/opt/master-bot/backups"
DATE=$(date +%Y%m%d_%H%M%S)

echo "💾 شروع پشتیبان‌گیری..."

mkdir -p $BACKUP_DIR

# Backup database
cp /opt/master-bot/master_bot.db $BACKUP_DIR/master_bot_$DATE.db

# Backup generated bots
tar -czf $BACKUP_DIR/generated_bots_$DATE.tar.gz /workspace/generated_bots/

# Backup configuration
cp /opt/master-bot/config.py $BACKUP_DIR/config_$DATE.py

# Keep only last 10 backups
cd $BACKUP_DIR
ls -t *.db | tail -n +11 | xargs rm -f 2>/dev/null
ls -t *.tar.gz | tail -n +11 | xargs rm -f 2>/dev/null
ls -t *.py | tail -n +11 | xargs rm -f 2>/dev/null

echo "✅ پشتیبان‌گیری کامل شد در: $BACKUP_DIR"
EOF

chmod +x /opt/master-bot/backup.sh

# Create log rotation configuration
echo "📋 تنظیم log rotation..."
cat > /etc/logrotate.d/master-bot << 'EOF'
/var/log/master-bot/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 master-bot master-bot
    postrotate
        systemctl reload master-bot
        systemctl reload master-bot-web
    endscript
}
EOF

# Set up firewall (if ufw is available)
if command -v ufw &> /dev/null; then
    echo "🔥 تنظیم فایروال..."
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 22/tcp
    ufw --force enable
fi

# Create monitoring script
cat > /opt/master-bot/monitor.sh << 'EOF'
#!/bin/bash

echo "📊 وضعیت ربات مادر:"
echo "===================="

echo "🤖 Master Bot Service:"
systemctl is-active master-bot

echo "🌐 Web Panel Service:"
systemctl is-active master-bot-web

echo "🔧 Nginx Service:"
systemctl is-active nginx

echo ""
echo "📈 آمار سیستم:"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory: $(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')"
echo "Disk: $(df -h / | awk 'NR==2{print $5}')"

echo ""
echo "🗄️ آمار دیتابیس:"
if [ -f "/opt/master-bot/master_bot.db" ]; then
    echo "تعداد ربات‌ها: $(sqlite3 /opt/master-bot/master_bot.db 'SELECT COUNT(*) FROM generated_bots;' 2>/dev/null || echo "N/A")"
    echo "ربات‌های فعال: $(sqlite3 /opt/master-bot/master_bot.db "SELECT COUNT(*) FROM generated_bots WHERE status='running';" 2>/dev/null || echo "N/A")"
else
    echo "دیتابیس یافت نشد"
fi
EOF

chmod +x /opt/master-bot/monitor.sh

# Set final permissions
chown -R master-bot:master-bot /opt/master-bot

# Reload systemd
systemctl daemon-reload

echo ""
echo "🎉 نصب با موفقیت کامل شد!"
echo "================================"
echo ""
echo "📋 مراحل بعدی:"
echo "1. توکن ربات مادر را از @BotFather دریافت کنید"
echo "2. فایل /opt/master-bot/config.py را ویرایش کنید:"
echo "   - MASTER_BOT_TOKEN را تنظیم کنید"
echo "   - ADMIN_ID را تنظیم کنید"
echo "3. برای راه‌اندازی: /opt/master-bot/start.sh"
echo ""
echo "🔧 دستورات مفید:"
echo "راه‌اندازی: /opt/master-bot/start.sh"
echo "متوقف کردن: /opt/master-bot/stop.sh"
echo "بروزرسانی: /opt/master-bot/update.sh"
echo "پشتیبان‌گیری: /opt/master-bot/backup.sh"
echo "مانیتورینگ: /opt/master-bot/monitor.sh"
echo ""
echo "📊 لاگ‌ها:"
echo "Master Bot: journalctl -u master-bot -f"
echo "Web Panel: journalctl -u master-bot-web -f"
echo "Nginx: journalctl -u nginx -f"
echo ""
echo "🌐 پنل وب پس از راه‌اندازی در آدرس زیر قابل دسترس است:"
echo "http://$(hostname -I | awk '{print $1}')"
echo "نام کاربری: admin"
echo "رمز عبور: admin123"
echo ""
echo "⚠️ حتما رمز عبور پیش‌فرض را تغییر دهید!"