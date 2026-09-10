# English for Baby

Family self-hosted web app for 5-year-old English reading practice.

## Features

- **Lesson Mode**: Parent creates lessons (image + text + TTS), child follows step by step
- **Challenge Mode**: Auto-picks weak sentences for focused practice
- **Completion Scoring**: Bag-of-words with fuzzy matching — answers "did the child read all the words?" (parent-only)
- **Daily Chart**: Line chart with dual Y-axes (count + score), date range picker
- **Celebration**: Confetti & stickers regardless of performance — scores are for parents only
- **Parent PIN Protection**: PBKDF2 challenge-response auth to protect parent dashboard
- **Recordings Auth**: Child recordings require parent auth to access (not publicly exposed)

## Architecture

| Layer | Stack |
|-------|-------|
| Frontend | React + Vite + TypeScript |
| Backend | FastAPI + SQLite |
| TTS | edge-tts / Tencent Cloud TTS |
| ASR | faster-whisper (small, cpu, int8) |

## Scoring Design

Completion scoring uses a **bag-of-words** approach — it only answers one question: "did the child read all the words in the target sentence?"

- **Filler words** (uh, um, er, ah, etc.) are discarded before scoring
- **Fuzzy matching** handles ASR quirks: stemming (cat/cats), edit distance for long words
- **Multiset semantics**: "the the cat" requires reading "the" twice
- **No penalty for extra words**: reading more than the target doesn't reduce score
- Pauses, stutters, and repeated words are naturally handled by the bag-of-words approach

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+

### 1. Install Dependencies

```bash
# Backend
cd server
pip install -r requirements.txt

# Frontend
cd web
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Start Services

```bash
# Backend
cd server
uvicorn server.main:app --reload --port 8001

# Frontend
cd web
npm run dev  # → http://localhost:5174
```

## Environment Variables

```bash
# ── Model Paths ──────────────────────────────────────────────

# Whisper model (ASR)
# Default: small (auto-downloaded from HuggingFace)
WHISPER_MODEL_PATH=./data/models/whisper

# ── TTS Config ──────────────────────────────────────────────

# Tencent Cloud TTS (optional, more stable)
TENCENT_SECRET_ID=your_secret_id
TENCENT_SECRET_KEY=your_secret_key

# ── CORS ────────────────────────────────────────────────────

# Comma-separated origins (leave empty for dev defaults)
# CORS_ORIGINS=http://localhost:80,http://192.168.1.100
```

### 国内 HuggingFace 镜像

Whisper 模型默认从 HuggingFace 下载，国内网络可能较慢。设置镜像环境变量：

```bash
# 方式一：在 .env 中添加
HF_ENDPOINT=https://hf-mirror.com

# 方式二：启动时传入
HF_ENDPOINT=https://hf-mirror.com uvicorn server.main:app --reload --port 8001
```

### Model Info

| Model | Purpose | Download | Size |
|-------|---------|----------|------|
| faster-whisper small | ASR speech recognition | Auto-download on first use | ~500MB |

## CORS 配置（局域网非 Docker 部署）

用 `npm run dev` 开发或直接 `uvicorn` 部署时，需要在 `.env` 中配置 CORS 允许局域网设备访问：

```bash
# 假设你的局域网 IP 是 192.168.1.100，iPad 通过 http://192.168.1.100:8001 访问
CORS_ORIGINS=http://localhost:5173,http://localhost:8001,http://192.168.1.100,http://192.168.1.100:8001
```

> Docker 部署（nginx 反代）不需要配置 CORS，因为前端和 API 走同一个域名。

## Project Structure

```
├── server/
│   ├── main.py              # FastAPI entry
│   ├── models.py            # SQLite tables
│   ├── schemas.py           # Pydantic request schemas
│   ├── database.py          # DB init
│   ├── routers/
│   │   ├── attempt.py       # Recording upload + ASR (auth-free by design — child uploads)
│   │   ├── history.py       # Daily stats, weak sentences, session history
│   │   ├── items.py         # CRUD + TTS generation (auth required)
│   │   ├── lessons.py       # Lesson management
│   │   ├── settings.py      # Key-value settings + PIN auth
│   │   └── upload.py        # Image upload (auth required)
│   ├── services/
│   │   ├── compare.py       # Completion scoring (bag-of-words)
│   │   ├── transcribe.py    # faster-whisper ASR
│   │   ├── tts.py           # edge-tts wrapper
│   │   └── tts_tencent.py   # Tencent Cloud TTS
│   └── data/                # Runtime data (git-ignored)
│       ├── models/          # AI models (whisper)
│       ├── audio/           # Generated TTS audio
│       ├── images/          # Uploaded images
│       ├── recordings/      # Child recordings
│       ├── app.db           # SQLite database
│       └── logs/            # Application logs
├── web/
│   ├── src/
│   │   ├── App.tsx           # Screen routing
│   │   ├── components/
│   │   │   ├── AdminGuard.tsx     # PIN authentication
│   │   │   ├── Challenge.tsx      # Child challenge mode
│   │   │   ├── Confetti.tsx       # Celebration animation
│   │   │   ├── DrillPlayer.tsx    # Child lesson player
│   │   │   └── LessonPicker.tsx   # Home + lesson list
│   │   ├── pages/
│   │   │   └── Admin.tsx          # Parent panel
│   │   └── utils/
│   │       ├── authFetch.ts       # Token-injecting fetch wrapper
│   │       └── recording.ts       # Shared recording utilities
│   └── vite.config.ts
├── deploy/                  # Deployment configs
│   ├── Dockerfile           # Multi-stage build (frontend + backend)
│   ├── docker-compose.yml   # Docker Compose orchestration (reads .env)
│   ├── nginx.conf           # Nginx reverse proxy config
│   ├── build.sh             # One-click deploy script
│   └── README_deploy.md     # LAN deployment guide
├── .env                     # Environment variables (git-ignored)
└── README.md
```

## Security

- **Parent auth**: PBKDF2-SHA256 challenge-response, session tokens, rate limiting
- **Recordings**: Require parent auth to access (header token or query param)
- **TTS generation**: Requires parent auth (prevents API abuse)
- **File uploads**: 10MB size limit on recordings and images

## Privacy & Data

本应用为**家庭自托管**，所有数据存储在你自己的设备上，不上传到任何第三方服务器。

### 数据内容

| 数据 | 存储位置 | 说明 |
|------|----------|------|
| 录音文件 | `server/data/recordings/` | 孩子的朗读录音（.webm/.mp4） |
| 图片 | `server/data/images/` | 课程配图 |
| TTS 音频 | `server/data/audio/` | 合成的朗读音频 |
| 练习记录 | `server/data/app.db` | SQLite 数据库（成绩、设置） |
| 日志 | `server/data/logs/` | 运行日志 |

### 删除数据

```bash
# 删除所有录音
rm -rf server/data/recordings/*

# 删除所有图片
rm -rf server/data/images/*

# 删除所有练习记录（重置数据库）
rm server/data/app.db
# 重启服务后会自动重建空数据库

# 彻底重置（删除所有数据）
rm -rf server/data/
```

## Browser Compatibility

- **Chrome/Edge**: Full support
- **Firefox**: Full support
- **Safari/iOS**: Requires HTTPS or localhost for microphone access
  - Uses MP4 audio format instead of WebM

## Deployment

See [deploy/README_deploy.md](deploy/README_deploy.md) for LAN deployment with Docker.

## Troubleshooting

### 孩子端录音没反应 / 家长面板看不到记录

检查浏览器控制台（F12）是否有 401 错误。录音上传接口 `/api/attempts` 不需要鉴权，如果出现 401 说明后端代码被意外修改，检查 `server/routers/attempt.py` 的 `create_attempt` 函数签名。

### Challenge 模式显示 "No weak sentences"

这可能是因为孩子还没有练习记录。先在 Lesson Mode 练习几轮，系统会自动识别薄弱句子。

### iPad Safari 无法录音

iPad 在 HTTP 下不允许使用麦克风。解决方案：
1. 使用 HTTPS（自签名证书或 Let's Encrypt）
2. 使用 ngrok 隧道：`ngrok http 8001`
3. 只用 Chrome/Edge 浏览器

### Whisper 模型下载失败 / 很慢

设置国内 HuggingFace 镜像：

```bash
HF_ENDPOINT=https://hf-mirror.com uvicorn server.main:app --reload --port 8001
```

或手动下载模型放到 `server/data/models/whisper/` 目录。

### Docker 构建失败

确保已安装 Docker 和 Docker Compose。运行 `docker --version` 和 `docker compose version`（或 `docker-compose --version`）检查。

### 录音回放 403 / 422

录音文件需要家长鉴权才能访问。确保管理员面板已登录，或在 URL 中加上 `?token=xxx`。

### 评分一直是 0%

检查 Whisper 模型是否正确加载。查看日志：`tail -f data/logs/app.log`，搜索 "Whisper model loaded"。

### 端口被占用

```bash
# 查找占用 8001 端口的进程
lsof -i :8001

# 改用其他端口
uvicorn server.main:app --reload --port 8002
```

## License

MIT
