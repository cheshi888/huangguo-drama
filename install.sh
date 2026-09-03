#!/usr/bin/env bash
# ============================================================
#  黄果短剧 - 一键安装（自动拉取代码 + 部署 + 后台常驻）
#  用法（推荐，一条命令）:
#    curl -fsSL https://raw.githubusercontent.com/cheshi888/huangguo-drama/main/install.sh | sudo bash
#  或（已下载脚本时）:
#    sudo bash install.sh
# ============================================================
set -e

REPO="${REPO:-cheshi888/huangguo-drama}"
GITHUB_URL="https://github.com/${REPO}.git"
APP_DIR="${APP_DIR:-/opt/huangguo-drama}"

if [ "$(id -u)" -ne 0 ]; then
  echo "[错误] 请用 root 运行：sudo bash install.sh"
  exit 1
fi

echo "=============================================="
echo "  黄果短剧 一键安装"
echo "=============================================="

# 1) 安装依赖 git + python3
echo "[1/4] 安装依赖 git / python3 ..."
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -y >/dev/null 2>&1 || true
  apt-get install -y git python3 >/dev/null 2>&1 || true
elif command -v yum >/dev/null 2>&1; then
  yum install -y git python3 >/dev/null 2>&1 || true
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y git python3 >/dev/null 2>&1 || true
else
  echo "[错误] 无法识别的包管理器，请手动安装 git 和 python3"
  exit 1
fi

# 校验依赖是否就绪
command -v git >/dev/null 2>&1 || { echo "[错误] git 安装失败，请手动安装"; exit 1; }
if command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "[错误] python3 安装失败，请手动安装"; exit 1
fi
echo "  依赖就绪：git $(git --version 2>&1 | awk '{print $3}') / $($PY --version 2>&1)"

# 2) 拉取代码
echo "[2/4] 拉取代码 ${REPO} ..."
if [ -d "${APP_DIR}/.git" ]; then
  echo "  已存在，执行 git pull 更新 ..."
  (cd "${APP_DIR}" && git pull)
else
  git clone "${GITHUB_URL}" "${APP_DIR}"
fi

# 3) 部署（生成 systemd 服务 + 开机自启 + 启动）
echo "[3/4] 部署并启动 ..."
bash "${APP_DIR}/deploy.sh"

echo "[4/4] 全部完成！"
