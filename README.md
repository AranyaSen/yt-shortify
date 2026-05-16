# YT Shorts Generator (SHORTIFY)

Turn any YouTube video into vertical short-form clips — **100% free and local**. No cloud APIs.

**Stack:** Django REST + React (Vite) + faster-whisper + LM Studio + yt-dlp + FFmpeg

## Prerequisites

| Tool | Purpose |
|------|---------|
| **Python 3.10+** | Django backend |
| **Node.js 18+** | React frontend |
| **FFmpeg** | Audio extract + vertical clip render |
| **LM Studio** | Local LLM for highlight detection |
| **yt-dlp** | Installed via pip (also needs FFmpeg for merges) |

### Install FFmpeg

- **Windows:** `winget install Gyan.FFmpeg` then **restart your terminal and Django server**. The app auto-detects the WinGet install path even if FFmpeg is not on `PATH`. Optional: add the `bin` folder to `PATH`, or set `FFMPEG_PATH` in `backend/config/settings.py`.
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

### LM Studio

1. Open LM Studio and load a model (e.g. **qwen3-8b**)
2. Start the local server on `http://127.0.0.1:1234`
3. Use the same model name in the UI

## Project structure

```
yt-shorts-gen/
├── backend/          # Django + pipeline
├── frontend/         # React + Vite + Tailwind
└── README.md
```

## Quick start

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — API calls proxy to Django on port 8000.

## Pipeline

1. Paste a YouTube URL → **Generate Shorts**
2. Download video (yt-dlp)
3. Optional: trim to a time range (e.g. `1:30` → `8:00`)
4. Extract audio + transcribe (FFmpeg + faster-whisper)
5. **Local LLM on:** LM Studio picks 3–5 engaging 30–60s segments automatically  
   **Local LLM off:** copy the generated prompt → paste into any LLM → paste JSON response back → app renders shorts
6. FFmpeg cuts vertical 1080×1920 MP4s with blurred letterbox background
7. Preview and download each short in the UI

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate/` | Start job `{ url, model?, num_shorts?, use_local_llm?, clip_start?, clip_end? }` |
| POST | `/api/continue/<job_id>/` | Submit manual LLM JSON `{ llm_response }` |
| GET | `/api/status/<job_id>/` | Poll progress + shorts list (+ `llm_prompt` when awaiting) |
| GET | `/api/download/<job_id>/<short_id>/` | Stream MP4 |
| DELETE | `/api/cleanup/<job_id>/` | Remove temp/output files |

## Configuration

Edit `backend/config/settings.py`:

- `LMSTUDIO_URL` — default `http://127.0.0.1:1234`
- `DEFAULT_MODEL` — default `qwen3-8b`
- `WHISPER_MODEL_SIZE` — default `base` (use `tiny` on low RAM)
- `JOB_CLEANUP_SECONDS` — auto-delete jobs after 1 hour

## Troubleshooting

| Issue | Fix |
|-------|-----|
| LM Studio not running | Start server in LM Studio |
| FFmpeg not found | Install FFmpeg and ensure it's on `PATH` |
| yt-dlp error | Check URL (private/age-restricted videos may fail) |
| Whisper OOM | Shorter video or `WHISPER_MODEL_SIZE = 'tiny'` |
| Invalid AI JSON | Try another model in LM Studio |

## License

MIT — use freely for personal projects.
