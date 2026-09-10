# 局域网部署指南

## 快速部署（推荐）

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone <repo-url>
cd english-for-baby

# 2. 一键构建并启动
cd deploy
./build.sh
```

脚本会自动：构建前端 → Docker 构建后端 → 启动服务

访问: `http://你的IP`（80 端口，nginx 托管前端 + 反代 API）

### 方式二：直接部署（无 Docker）

```bash
# 1. 安装后端依赖
cd server
pip install -r requirements.txt

# 2. 安装前端依赖并构建
cd ../web
npm install
npm run build

# 3. 启动后端
cd ..
uvicorn server.main:app --host 0.0.0.0 --port 8001
```

> ⚠️ 方式二只提供 API 服务（端口 8001），前端需要单独部署（如 nginx）或使用 `npm run dev` 开发模式。

访问: `http://你的IP:8001`（仅 API，无前端页面）

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

1. 用 iPad/手机打开 `http://你的IP`
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

- **Whisper**: 首次使用自动下载（约 500MB），下载到 `data/models/` 目录
- 无需手动下载其他模型

### 环境变量

复制 `.env.example` 为 `.env`，填入你的配置：

```bash
cp .env.example .env
# 编辑 .env 填入腾讯云 TTS 密钥等
```

## 生产环境建议

1. **使用反向代理**
   ```bash
   # Nginx 配置示例见 deploy/nginx.conf
   # 已配置 client_max_body_size 10m 支持录音上传
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

## 架构说明

Docker 部署包含两个容器：

| 容器 | 端口 | 职责 |
|------|------|------|
| `peppa-backend` | 8001 | FastAPI 后端（API + 鉴权录音流式端点） |
| `peppa-nginx` | 80 | 前端静态文件 + API 反向代理 |

- 前端构建产物在 Docker 构建时打包进镜像，通过 nginx 提供服务
- `/api/*` 和 `/data/*` 请求反代到后端
- 录音文件（`/data/recordings/*`）需要鉴权才能访问
