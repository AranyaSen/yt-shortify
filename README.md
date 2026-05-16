# YT Shorts Generator (SHORTIFY)



Turn any YouTube video into vertical short-form clips — **100% free and local**. No cloud APIs.



**Stack:** Django REST + React (Vite) + faster-whisper + LM Studio + yt-dlp + FFmpeg.wasm (browser)



## Prerequisites



| Tool | Purpose |

|------|---------|

| **Python 3.10+** | Django backend |

| **Node.js 18+** | React frontend |

| **LM Studio** | Local LLM for highlight detection (optional if using manual LLM) |

| **yt-dlp** | Installed via pip (downloads single-file MP4 when available) |



**No system FFmpeg required.** Vertical clip rendering runs in the browser via FFmpeg.wasm.



### LM Studio



1. Open LM Studio and load a model (e.g. **qwen3-8b**)

2. Start the local server on `http://127.0.0.1:1234`

3. Use the same model name in the UI



## Project structure



```

yt-shorts-gen/

├── backend/          # Django + pipeline

├── frontend/         # React + Vite + Tailwind + FFmpeg.wasm

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

2. Download video (yt-dlp, no merge when a single MP4 is available)

3. Optional time range: Whisper transcribes only that segment (no server-side trim)

4. Transcribe with faster-whisper (directly from the video file)

5. **Local LLM on:** LM Studio picks 3–5 engaging 30–60s segments automatically  

   **Local LLM off:** copy the generated prompt → paste into any LLM → paste JSON response back

6. **Browser:** FFmpeg.wasm cuts vertical 1080×1920 MP4s (fast scale+pad; multi-threaded core)

7. Preview and download each short in the UI (blob URLs, no server render step)



## API



| Method | Endpoint | Description |

|--------|----------|-------------|

| POST | `/api/generate/` | Start job `{ url, model?, num_shorts?, use_local_llm?, clip_start?, clip_end? }` |

| POST | `/api/continue/<job_id>/` | Submit manual LLM JSON `{ llm_response }` |

| GET | `/api/status/<job_id>/` | Poll progress + shorts list (+ `llm_prompt` when awaiting) |

| GET | `/api/source/<job_id>/` | Stream downloaded source video for browser rendering |

| POST | `/api/render-complete/<job_id>/` | Mark job done after client-side render |

| GET | `/api/download/<job_id>/<short_id>/` | Stream MP4 (legacy; clips are rendered in browser) |

| DELETE | `/api/cleanup/<job_id>/` | Remove temp files |



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

| Browser render fails | Use Chrome/Edge; keep the tab open; first run downloads ~30MB WASM from unpkg |

| yt-dlp error | Check URL (private/age-restricted videos may fail); some formats need a single-file MP4 |

| Whisper OOM | Shorter video or `WHISPER_MODEL_SIZE = 'tiny'` |

| Invalid AI JSON | Try another model in LM Studio |



## License



MIT — use freely for personal projects.

