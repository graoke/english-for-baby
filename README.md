# English for Baby

Family self-hosted web app for 5-year-old English reading practice.

## Features

- **Lesson Mode**: Parent creates lessons (image + text + TTS), child follows step by step
- **Challenge Mode**: Auto-picks weak sentences for focused practice
- **Completion Scoring**: Bag-of-words with fuzzy matching — answers "did the child read all the words?" (parent-only)
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
```

### Model Info

| Model | Purpose | Download | Size |
|-------|---------|----------|------|
| faster-whisper small | ASR speech recognition | Auto-download on first use | ~500MB |

## Project Structure

```
├── server/
│   ├── main.py              # FastAPI entry
│   ├── models.py            # SQLite tables
│   ├── schemas.py           # Pydantic request schemas
│   ├── database.py          # DB init
│   ├── routers/
│   │   ├── attempt.py       # Recording upload + ASR
│   │   ├── history.py       # Daily stats, weak sentences, session history
│   │   ├── items.py         # CRUD + TTS generation
│   │   ├── lessons.py       # Lesson management
│   │   ├── settings.py      # Key-value settings + PIN auth
│   │   └── upload.py        # Image upload
│   └── services/
│       ├── compare.py       # Completion scoring (bag-of-words)
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
│   │   │   └── LessonPicker.tsx   # Home + lesson list
│   │   ├── pages/
│   │   │   └── Admin.tsx          # Parent panel
│   │   └── utils/
│   │       ├── authFetch.ts       # Token-injecting fetch wrapper
│   │       └── recording.ts       # Shared recording utilities
│   └── vite.config.ts
├── data/                    # Runtime data
│   ├── models/              # AI models (whisper)
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

- View practice history with "读出 X / Y 个词" and missed words
- PIN protection (stored in database)
- Configure TTS mode and display settings

## License

MIT
