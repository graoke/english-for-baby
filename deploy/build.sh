#!/bin/bash
set -e

# 获取脚本所在目录（deploy/）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# 项目根目录
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# 兼容 docker compose（v2）和 docker-compose（v1）
if docker compose version &>/dev/null; then
    DC="docker compose"
else
    DC="docker-compose"
fi

echo "=== Peppa Reader 局域网部署 ==="
echo "项目根目录: $ROOT_DIR"
echo "Docker 命令: $DC"

# 1. 构建前端
echo "📦 构建前端..."
cd "$ROOT_DIR/web"
npm install
npm run build
cd "$ROOT_DIR"

# 2. 确保 .env 存在
if [ ! -f "$ROOT_DIR/.env" ]; then
    echo "⚠️  .env 文件不存在，从 .env.example 创建..."
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    echo "📝 已创建 .env，请根据需要编辑配置（如腾讯云 TTS 密钥、HuggingFace 镜像等）"
fi

# 3. 确保数据目录存在
echo "📁 创建数据目录..."
mkdir -p server/data/models server/data/audio server/data/images server/data/recordings server/data/logs

# 3. Docker 构建（从 deploy/ 目录）
echo "🐳 Docker 构建..."
cd "$SCRIPT_DIR"
$DC build
cd "$ROOT_DIR"

# 4. 启动服务
echo "🚀 启动服务..."
cd "$SCRIPT_DIR"
$DC up -d
cd "$ROOT_DIR"

# 5. 获取本机 IP（兼容 macOS 和 Linux）
if command -v ifconfig &>/dev/null; then
    LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
elif command -v hostname &>/dev/null; then
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
else
    LOCAL_IP="localhost"
fi

echo ""
echo "✅ 部署完成！"
echo ""
echo "📱 局域网访问地址: http://${LOCAL_IP}"
echo "💻 本机访问地址: http://localhost"
echo ""
echo "⚠️  注意：当前为 HTTP 模式，iPad Safari 无法使用录音功能"
echo "   如需 iPad 录音，请使用 HTTPS（参见 deploy/README_deploy.md）"
echo ""
echo "📌 首次使用请设置家长面板 PIN"
echo ""
echo "查看日志: cd deploy && $DC logs -f"
echo "停止服务: cd deploy && $DC down"
