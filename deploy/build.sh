#!/bin/bash
set -e

echo "=== Peppa Reader 局域网部署 ==="

# 1. 构建前端
echo "📦 构建前端..."
cd web
npm run build
cd ..

# 2. 创建数据目录
echo "📁 创建数据目录..."
mkdir -p data/models data/audio data/images data/recordings data/logs

# 3. 下载 Whisper 模型（如果不存在）
if [ ! -d "data/models/whisper" ]; then
    echo "📥 首次运行，Whisper 模型会在启动时自动下载..."
fi

# 4. 检查 MiniCPM 模型
if [ ! -f "data/models/minicpm-phonetic-evaluator-q4_k_m.gguf" ]; then
    echo "⚠️  MiniCPM 模型未找到（音素评估功能不可用）"
    echo "   请下载 GGUF 文件放到 data/models/ 目录"
fi

# 5. Docker 构建
echo "🐳 Docker 构建..."
docker-compose build

# 6. 启动服务
echo "🚀 启动服务..."
docker-compose up -d

# 7. 获取本机 IP
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)

echo ""
echo "✅ 部署完成！"
echo ""
echo "📱 局域网访问地址: http://${LOCAL_IP}:5174"
echo "💻 本机访问地址: http://localhost:5174"
echo ""
echo "📌 首次使用请设置家长面板 PIN"
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
