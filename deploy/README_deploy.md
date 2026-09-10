# 局域网部署指南

## 快速部署（推荐）

### 方式一：Docker 部署

```bash
# 1. 克隆项目
git clone <repo-url>
cd peppa_reader

# 2. 构建前端
cd web && npm install && npm run build && cd ..

# 3. 启动服务
docker-compose up -d

# 4. 访问
# 本机: http://localhost:5174
# 局域网: http://你的IP:5174
```

### 方式二：直接部署

```bash
# 1. 安装后端依赖
cd server
pip install -r requirements.txt

# 2. 安装前端依赖并构建
cd ../web
npm install
npm run build

# 3. 启动后端（会自动托管前端静态文件）
cd ..
uvicorn server.main:app --host 0.0.0.0 --port 8001
```

访问: `http://你的IP:8001`

## 获取局域网 IP

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}'

# Linux
hostname -I

# Windows
ipconfig
```

## 首次使用

1. 用 iPad/手机打开 `http://你的IP:5174`
2. 点击右上角 👨‍👩‍👧 进入家长面板
3. 首次使用会要求设置 PIN（4-8 位）
4. 设置后每次进入都需要输入 PIN

## 注意事项

### Safari/iOS 录音问题

iPad 在 HTTP 局域网访问时无法使用麦克风。解决方案：

1. **使用 HTTPS**（推荐）
   ```bash
   # 生成自签名证书
   openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes
   
   # 使用 uvicorn 的 SSL 支持
   uvicorn server.main:app --host 0.0.0.0 --port 8001 --ssl-keyfile=key.pem --ssl-certfile=cert.pem
   ```

2. **使用 localhost 隧道**
   ```bash
   # 使用 ngrok 或类似工具
   ngrok http 8001
   ```

3. **只用 Chrome/Edge**
   - 这些浏览器在 HTTP 下也支持录音

### 模型文件

- **Whisper**: 首次使用自动下载（约 500MB）
- **MiniCPM**: 需要手动下载（约 2GB），放到 `data/models/` 目录

## 生产环境建议

1. **使用反向代理**
   ```bash
   # Nginx 配置示例见 deploy/nginx.conf
   ```

2. **配置 HTTPS**
   ```bash
   # 使用 Let's Encrypt 或自签名证书
   ```

3. **设置开机自启**
   ```bash
   # Docker Compose 已默认配置 restart: unless-stopped
   ```

4. **备份数据**
   ```bash
   # 重要数据在 data/ 目录
   tar -czf peppa_backup_$(date +%Y%m%d).tar.gz data/
   ```
