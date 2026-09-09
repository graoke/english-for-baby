# English for Baby

Family self-hosted web app for 5-year-old English reading practice.

## Features

- **Lesson Mode**: Parent creates lessons (image + text + TTS), child follows step by step
- **Challenge Mode**: Auto-picks weak sentences for focused practice
- **Two-stage Scoring**: Exact word match + MiniCPM phonetic judge (parent-only)
- **Daily Chart**: Line chart with dual Y-axes (count + score), date range picker
- **Celebration**: Confetti & stickers regardless of performance — scores are for parents only

## Inspiration

- [read-along-ai](https://github.com/kingkw1/read-along-ai) — core concept of guided reading practice
- [posy-pip-picture-book](https://github.com/FutaoSmile/posy-pip-picture-book) — UI/visual style reference

## Architecture

| Layer | Stack |
|-------|-------|
| Frontend | React + Vite + TypeScript |
| Backend | FastAPI + SQLite |
| TTS | edge-tts |
| ASR | faster-whisper (small, cpu, int8) |
| Phonetic Judge | MiniCPM GGUF via llama-cpp-python |

## Quick Start

```bash
# Backend
cd server
pip install -r requirements.txt
uvicorn server.main:app --reload --port 8001

# Frontend
cd web
npm install
npm run dev  # → http://localhost:5174
```

## Configuration

Backend runs on port `8001`, frontend on `5174`. CORS is configured for both `localhost:5173` and `localhost:5174`.

Settings are stored in SQLite `settings` table. Key setting: `show_text` (controls whether text is shown in child practice mode).

## Project Structure

```
├── server/
│   ├── main.py              # FastAPI entry, MiniCPM preload
│   ├── models.py            # SQLite tables
│   ├── database.py          # DB init
│   ├── routers/
│   │   ├── attempt.py       # Recording upload + ASR
│   │   ├── history.py       # Daily stats, weak sentences, challenge
│   │   ├── items.py         # CRUD + TTS generation
│   │   └── settings.py      # Key-value settings
│   └── services/
│       ├── compare.py       # Two-stage scoring (exact → MiniCPM)
│       ├── transcribe.py    # faster-whisper ASR
│       └── tts.py           # edge-tts wrapper
├── web/
│   ├── src/
│   │   ├── App.tsx           # Screen routing
│   │   ├── components/
│   │   │   ├── Challenge.tsx      # Child challenge mode
│   │   │   ├── Confetti.tsx       # Celebration animation
│   │   │   ├── DrillPlayer.tsx    # Child lesson player
│   │   │   └── LessonPicker.tsx   # Home + lesson list
│   │   └── pages/
│   │       └── Admin.tsx          # Parent panel
│   └── vite.config.ts
└── README.md
```
