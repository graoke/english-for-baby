# English for Baby

Family self-hosted web app for 5-year-old English reading practice.

## Features

- **Lesson Mode**: Parent creates lessons (image + text + TTS), child follows step by step
- **Challenge Mode**: Auto-picks weak sentences for focused practice
- **Two-stage Scoring**: Exact word match + MiniCPM phonetic judge (parent-only)
- **Daily Chart**: Line chart with dual Y-axes (count + score), date range picker
- **Celebration**: Confetti & stickers regardless of performance — scores are for parents only
- **Parent PIN Protection**: Simple PIN to protect parent dashboard

## Architecture

| Layer | Stack |
|-------|-------|
| Frontend | React + Vite + TypeScript |
| Backend | FastAPI + SQLite |
| TTS | edge-tts / Tencent Cloud TTS |
| ASR | faster-whisper (small, cpu, int8) |
| Phonetic Judge | MiniCPM GGUF via llama-cpp-python |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- (Optional) MiniCPM GGUF model for phonetic scoring

### 1. 安装依赖

```bash
# Backend
cd server
pip install -r requirements.txt

# Frontend
cd web
npm install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，配置模型路径：

```bash
cp .env.example .env
```

### 3. 下载模型

```bash
# 创建模型目录
mkdir -p data/models

# 下载 Whisper 模型（首次使用自动下载，或手动下载）
# 自动下载会存到 data/models/whisper 目录

# 下载 MiniCPM GGUF 模型（音素评估，可选）
# 将 .gguf 文件放到 data/models/ 目录
```

### 4. 启动服务

```bash
# Backend
cd server
uvicorn server.main:app --reload --port 8001

# Frontend
cd web
npm run dev  # → http://localhost:5174
```

## 环境变量配置

在 `.env` 文件中配置：

```bash
# ── 模型路径 ──────────────────────────────────────────────

# Whisper 模型（ASR 语音识别）
# 默认: data/models/whisper（首次使用自动下载）
WHISPER_MODEL_PATH=./data/models/whisper

# MiniCPM GGUF 模型（音素评估，可选）
# 需要手动下载 GGUF 文件
MINICPM_GGUF_PATH=./data/models/minicpm-phonetic-evaluator-q4_k_m.gguf

# ── TTS 配置 ──────────────────────────────────────────────

# 腾讯云 TTS（可选，更稳定）
TENCENT_SECRET_ID=your_secret_id
TENCENT_SECRET_KEY=your_secret_key
```

### 模型说明

| 模型 | 用途 | 下载方式 | 大小 |
|------|------|----------|------|
| faster-whisper small | ASR 语音识别 | 首次自动下载 | ~500MB |
| MiniCPM GGUF | 音素评估 | 手动下载 | ~2GB |

**Whisper**: 默认从 HuggingFace 自动下载到 `data/models/whisper`，无需手动操作。

**MiniCPM**: 需要手动下载 GGUF 文件（Q4_K_M 量化版本），放到 `data/models/` 目录。

## Project Structure

```
├── server/
│   ├── main.py              # FastAPI entry, MiniCPM preload
│   ├── models.py            # SQLite tables
│   ├── database.py          # DB init
│   ├── routers/
│   │   ├── attempt.py       # Recording upload + ASR
│   │   ├── history.py       # Daily stats, weak sentences, session history
│   │   ├── items.py         # CRUD + TTS generation
│   │   ├── lessons.py       # Lesson management
│   │   ├── settings.py      # Key-value settings + PIN auth
│   │   └── upload.py        # Image upload
│   └── services/
│       ├── compare.py       # Two-stage scoring (exact → MiniCPM)
│       ├── transcribe.py    # faster-whisper ASR
│       ├── tts.py           # edge-tts wrapper
│       └── tts_tencent.py   # Tencent Cloud TTS
├── web/
│   ├── src/
│   │   ├── App.tsx           # Screen routing
│   │   ├── components/
│   │   │   ├── AdminGuard.tsx     # PIN authentication
│   │   │   ├── Challenge.tsx      # Child challenge mode
│   │   │   ├── Confetti.tsx       # Celebration animation
│   │   │   ├── DrillPlayer.tsx    # Child lesson player
│   │   │   ├── LessonPicker.tsx   # Home + lesson list
│   │   │   └── Recorder.tsx       # Recording component (Safari compatible)
│   │   ├── pages/
│   │   │   └── Admin.tsx          # Parent panel
│   │   └── utils/
│   │       └── authFetch.ts       # Token-injecting fetch wrapper
│   └── vite.config.ts
├── data/                    # Runtime data
│   ├── models/              # AI models (whisper, minicpm)
│   ├── audio/               # Generated TTS audio
│   ├── images/              # Uploaded images
│   ├── recordings/          # Child recordings
│   └── logs/                # Application logs
├── .env                     # Environment variables
└── README.md
```

## Browser Compatibility

- **Chrome/Edge**: Full support
- **Firefox**: Full support
- **Safari/iOS**: Requires HTTPS or localhost for microphone access
  - Uses MP4 audio format instead of WebM

## Parent Features

- View practice history and weak sentences
- PIN protection (stored in database)
- Configure TTS mode and display settings

## Known Limitations

- MiniCPM model requires manual download
- No mobile app (web app works on tablets)

## License

MIT
