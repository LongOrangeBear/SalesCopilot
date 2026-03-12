# VPS Setup Guide -- SalesCopilot

Полное руководство по настройке VPS для SalesCopilot с нуля.

## Требования

- Ubuntu 22.04+ / Debian 12+
- Root-доступ
- Git, Python 3.10+, Node.js 18+, npm, nginx

## 1. Установка зависимостей

```bash
apt update && apt upgrade -y
apt install -y git python3 python3-venv python3-pip nginx curl

# Node.js 20.x (через NodeSource)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
```

## 2. Клонирование проекта

```bash
mkdir -p /opt/salescopilot
cd /opt/salescopilot
git clone https://github.com/LongOrangeBear/SalesCopilot.git .
```

## 3. Backend -- настройка

```bash
cd /opt/salescopilot/backend

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Создать .env (заполнить актуальными ключами!)
cp .env.example .env
nano .env
```

### Содержимое .env

```env
# Yandex Cloud (SpeechKit STT)
YANDEX_API_KEY=<yandex_api_key>
YANDEX_FOLDER_ID=<yandex_folder_id>

# OpenAI (GPT)
OPENAI_API_KEY=<openai_api_key>

# Asterisk
ASTERISK_HOST=<server_ip>
ASTERISK_ARI_PORT=8088
ASTERISK_ARI_USER=admin
ASTERISK_ARI_PASSWORD=

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Dashboard URL (production)
DASHBOARD_URL=http://<server_ip>
```

## 4. Dashboard -- сборка

```bash
cd /opt/salescopilot/dashboard
npm ci
npm run build
```

## 5. Systemd -- backend сервис

```bash
cat > /etc/systemd/system/salescopilot-backend.service << 'EOF'
[Unit]
Description=SalesCopilot Backend (FastAPI/Uvicorn)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/salescopilot/backend
Environment=PATH=/opt/salescopilot/backend/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/salescopilot/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable salescopilot-backend
systemctl start salescopilot-backend
```

## 6. Nginx -- конфигурация

```bash
cat > /etc/nginx/sites-available/salescopilot << 'EOF'
server {
    listen 80;
    server_name _;

    # Dashboard - serve built static files
    root /opt/salescopilot/dashboard/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket proxy
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
EOF

ln -sf /etc/nginx/sites-available/salescopilot /etc/nginx/sites-enabled/salescopilot
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

## 7. Deploy скрипт

```bash
cat > /opt/salescopilot/deploy.sh << 'DEPLOY'
#!/bin/bash
set -e

echo "[deploy] Starting deployment..."
cd /opt/salescopilot

# Pull latest code
echo "[deploy] Pulling latest code..."
git pull origin main

# Get version info
COMMIT_COUNT=$(git rev-list --count HEAD)
COMMIT_HASH=$(git rev-parse --short HEAD)
DEPLOY_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Backend: update dependencies & restart
echo "[deploy] Updating backend..."
cd /opt/salescopilot/backend
source venv/bin/activate
pip install -r requirements.txt -q 2>&1 | tail -3
deactivate

echo "[deploy] Restarting backend service..."
systemctl restart salescopilot-backend

# Dashboard: reinstall deps & rebuild
echo "[deploy] Building dashboard..."
cd /opt/salescopilot/dashboard
npm ci --loglevel=error 2>&1 | tail -3
npm run build 2>&1 | tail -5

# Generate version.json
cat > /opt/salescopilot/dashboard/dist/version.json << VERJSON
{
  "version": "0.1.${COMMIT_COUNT}",
  "commit": "${COMMIT_HASH}",
  "buildNumber": ${COMMIT_COUNT},
  "deployedAt": "${DEPLOY_TIME}"
}
VERJSON

# Reload nginx
echo "[deploy] Reloading nginx..."
systemctl reload nginx

echo "[deploy] Deployment complete! Version: 0.1.${COMMIT_COUNT} (${COMMIT_HASH})"
DEPLOY

chmod +x /opt/salescopilot/deploy.sh
```

## 8. GitHub Actions -- SSH deploy key

Для автоматического деплоя через GitHub Actions:

```bash
# Сгенерировать deploy key на сервере
ssh-keygen -t ed25519 -f /root/.ssh/deploy_key -N "" -C "deploy@salescopilot"

# Добавить публичный ключ в authorized_keys
cat /root/.ssh/deploy_key.pub >> /root/.ssh/authorized_keys
```

Далее в GitHub репозитории:

1. **Settings -> Secrets and variables -> Actions**
2. Добавить секреты:

| Secret | Значение |
|--------|----------|
| `VPS_HOST` | IP-адрес сервера |
| `VPS_USER` | `root` |
| `VPS_SSH_KEY` | Содержимое `/root/.ssh/deploy_key` (приватный ключ) |
| `VPS_PORT` | `22` |

## 9. Проверка

```bash
# Backend работает
curl http://localhost:8000/health

# Dashboard доступен
curl -I http://localhost

# Сервисы активны
systemctl status salescopilot-backend
systemctl is-active nginx

# Версия
cat /opt/salescopilot/dashboard/dist/version.json
```

## 10. Firewall (рекомендуется)

```bash
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 5060/udp   # SIP (Asterisk)
ufw allow 8088/tcp   # Asterisk ARI
ufw allow 10000:20000/udp  # RTP (Asterisk)
ufw enable
```
