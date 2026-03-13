#!/bin/bash
# SalesCopilot -- скрипт деплоя на VPS
# Вызывается из GitHub Actions (appleboy/ssh-action)
set -euo pipefail

APP_DIR="/opt/salescopilot"
BRANCH="main"

echo "=== [1/6] Pull latest code ==="
cd "$APP_DIR"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

echo "=== [2/6] Backend: install dependencies ==="
cd "$APP_DIR/backend"
source venv/bin/activate
pip install -q -r requirements.txt

echo "=== [3/6] Dashboard: install dependencies ==="
cd "$APP_DIR/dashboard"
npm ci --silent

echo "=== [4/6] Dashboard: build ==="
npm run build

echo "=== [5/6] Generate version.json ==="
COMMIT=$(git -C "$APP_DIR" rev-parse --short HEAD)
BUILD_NUM=$(git -C "$APP_DIR" rev-list --count HEAD)
DEPLOY_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "$APP_DIR/dashboard/dist/version.json" <<EOF
{
  "version": "0.1.${BUILD_NUM}",
  "commit": "${COMMIT}",
  "buildNumber": ${BUILD_NUM},
  "deployedAt": "${DEPLOY_TIME}"
}
EOF
echo "Version: 0.1.${BUILD_NUM} (${COMMIT})"

echo "=== [6/6] Restart services ==="
systemctl restart salescopilot-backend
systemctl reload nginx

echo "=== Deploy complete ==="
