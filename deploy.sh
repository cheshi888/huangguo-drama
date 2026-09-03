#!/usr/bin/env bash
# ============================================================
#  黄果短剧 - Linux VPS 一键部署脚本
#  用法: sudo bash deploy.sh
#  功能: 检测环境 -> 生成 systemd 服务 -> 开机自启 + 常驻运行
# ============================================================
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="huangguo"
PORT="${PANEL_PORT:-8788}"

# 打印播放地址 / 订阅地址 / 快捷指令
print_info() {
  # 公网 IPv4 优先（-4 强制走 IPv4，避免取到 IPv6）
  IP=$(curl -4 -s --max-time 5 ip.sb 2>/dev/null)
  [ -z "$IP" ] && IP=$(curl -4 -s --max-time 5 ifconfig.me 2>/dev/null)
  [ -z "$IP" ] && IP=$(curl -4 -s --max-time 5 api.ipify.org 2>/dev/null)
  [ -z "$IP" ] && IP=$(hostname -I 2>/dev/null | awk '{print $1}')
  [ -z "$IP" ] && IP="你的服务器IP"
  echo ""
  echo "  ============== 黄果短剧 =============="
  echo "  播放面板 : http://${IP}:${PORT}/"
  echo "  订阅地址 : http://${IP}:${PORT}/playlist.m3u8"
  echo "  ======================================"
  echo ""
  echo "  快捷指令："
  echo "    查看状态 : systemctl status ${SERVICE_NAME}"
  echo "    实时日志 : journalctl -u ${SERVICE_NAME} -f"
  echo "    重启服务 : systemctl restart ${SERVICE_NAME}"
  echo "    更新代码 : cd ${APP_DIR} && git pull && systemctl restart ${SERVICE_NAME}"
  echo ""
  echo "  重新打印本信息 : bash ${APP_DIR}/deploy.sh info"
  echo ""
}

# 只打印信息（无需 root）
if [ "$1" = "info" ]; then
  print_info
  exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "[错误] 请用 root 运行: sudo bash deploy.sh"
  exit 1
fi

echo "=============================================="
echo "  黄果短剧 VPS 部署"
echo "=============================================="

# 1) 检测 Python3
PYTHON_BIN=""
for p in python3 python; do
  if command -v "$p" >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v "$p")"
    break
  fi
done
if [ -z "$PYTHON_BIN" ]; then
  echo "[错误] 未找到 Python3。请先安装："
  echo "  Debian/Ubuntu: apt update && apt install -y python3"
  echo "  CentOS:        yum install -y python3"
  exit 1
fi
echo "[1/4] Python: $("$PYTHON_BIN" --version 2>&1)"

# 2) 生成 systemd 服务
echo "[2/4] 生成 systemd 服务 ${SERVICE_NAME}.service ..."
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Huangguo Drama Player & Daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
ExecStart=${PYTHON_BIN} ${APP_DIR}/daemon.py
Restart=always
RestartSec=10
Environment=PANEL_PORT=${PORT}
Environment=PYTHONUNBUFFERED=1
Environment=REFRESH_MINUTES=30
Environment=REFRESH_AGE_SECONDS=1800
Environment=SCAN_LIMIT=3
Environment=FULL_SCAN_EVERY=12
Environment=CRAWL_WORKERS=12

[Install]
WantedBy=multi-user.target
EOF

# 3) 启动服务
echo "[3/4] 启动并设置开机自启 ..."
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}" >/dev/null 2>&1 || true
systemctl restart "${SERVICE_NAME}"

# 4) 完成
echo "[4/4] 部署完成！"
print_info
echo "  修改刷新间隔等配置：编辑 ${SERVICE_FILE}"
echo "  然后: systemctl daemon-reload && systemctl restart ${SERVICE_NAME}"
echo ""
echo "  注意：若无法访问，请放行端口 ${PORT}："
echo "    ufw 允许:      ufw allow ${PORT}/tcp"
echo "    firewalld 允许: firewall-cmd --add-port=${PORT}/tcp --permanent && firewall-cmd --reload"
