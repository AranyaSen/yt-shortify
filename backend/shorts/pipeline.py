import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import yt_dlp
from django.conf import settings
from faster_whisper import WhisperModel

from shorts import job_store
from shorts.ffmpeg_util import ffmpeg_bin_dir, resolve_ffmpeg


def update_job(job_id: str, **kwargs):
    job_store.update_job(job_id, **kwargs)


def _job_dir(job_id: str) -> Path:
    d = settings.TEMP_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _output_dir(job_id: str) -> Path:
    d = settings.OUTPUT_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _find_source_video(job_dir: Path) -> Path:
    for name in ('trimmed.mp4', 'source.mp4', 'source.mkv', 'source.webm'):
        p = job_dir / name
        if p.exists():
            return p
    for f in job_dir.iterdir():
        if f.suffix.lower() in ('.mp4', '.mkv', '.webm', '.mov'):
            return f
    raise FileNotFoundError('Downloaded video not found')


def build_llm_prompt(transcript: str, num_shorts: int) -> str:
    return f'''You are a viral video editor. Analyze this transcript and find the {num_shorts} most engaging moments that would make great short-form vertical videos (YouTube Shorts / TikTok / Reels). Keep few seconds before engagement start and end to avoid aggressive editing.

Rules:
- Each clip must be 30–60 seconds long
- Pick moments with: strong hooks, emotional peaks, surprising facts, storytelling climaxes, or actionable advice
- Clips must not overlap
- Return ONLY a valid JSON array, no explanation, no markdown, no code fences

Transcript with timestamps:
{transcript}

Return this exact JSON format example:
[
  {{
    "start_time": 55.2,
    "end_time": 98.7,
    "title": "The moment everything changed",
    "hook": "Nobody expected this to happen...",
    "reason": "Emotional peak with surprising reveal"
  }}
]'''


def _download_video(job_id: str, url: str) -> Path:
    job_dir = _job_dir(job_id)
    out_template = str(job_dir / 'source.%(ext)s')

    resolve_ffmpeg()

    ydl_opts = {
        'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
        'outtmpl': out_template,
        'merge_output_format': 'mp4',
        'ffmpeg_location': str(ffmpeg_bin_dir()),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        err = str(e)
        if 'ffmpeg is not installed' in err.lower() or 'ffmpeg' in err.lower():
            raise RuntimeError(
                'FFmpeg not found. Install: winget install Gyan.FFmpeg '
                '(then restart Django), or set FFMPEG_PATH in settings.py'
            ) from e
        raise RuntimeError(err) from e

    return _find_source_video(job_dir)


def _trim_source(
    source: Path,
    job_dir: Path,
    clip_start: float | None,
    clip_end: float | None,
) -> Path:
    if clip_start is None and clip_end is None:
        return source

    start = float(clip_start or 0)
    out = job_dir / 'trimmed.mp4'
    ffmpeg = str(resolve_ffmpeg())
    cmd = [ffmpeg, '-y', '-i', str(source), '-ss', str(start)]
    if clip_end is not None:
        cmd.extend(['-to', str(float(clip_end))])
    cmd.extend([
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        str(out),
    ])
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise RuntimeError(
            'FFmpeg not found. Install: winget install Gyan.FFmpeg '
            '(then restart Django), or set FFMPEG_PATH in settings.py'
        ) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.stderr or 'FFmpeg video trim failed') from e
    return out


def _extract_audio(source: Path, job_dir: Path) -> Path:
    audio_path = job_dir / 'audio.wav'
    ffmpeg = str(resolve_ffmpeg())
    cmd = [
        ffmpeg, '-y', '-i', str(source),
        '-vn', '-acodec', 'pcm_s16le',
        '-ar', '16000', '-ac', '1',
        str(audio_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise RuntimeError(
            'FFmpeg not found. Install: winget install Gyan.FFmpeg '
            '(then restart Django), or set FFMPEG_PATH in settings.py'
        ) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.stderr or 'FFmpeg audio extraction failed') from e
    return audio_path


def _transcribe(audio_path: Path) -> str:
    try:
        model = WhisperModel(
            settings.WHISPER_MODEL_SIZE,
            device='cpu',
            compute_type='int8',
        )
        segments, _ = model.transcribe(
            str(audio_path),
            word_timestamps=True,
        )
    except MemoryError:
        raise RuntimeError(
            'Transcription failed — try a shorter video'
        ) from None
    except Exception as e:
        err = str(e).lower()
        if 'memory' in err or 'oom' in err:
            raise RuntimeError(
                'Transcription failed — try a shorter video'
            ) from e
        raise

    lines = []
    for seg in segments:
        lines.append(f'[{seg.start:.1f}s] {seg.text.strip()}')
    return '\n'.join(lines)


def _parse_llm_json(text: str) -> list:
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```\s*$', '', text)
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        text = match.group(0)
    return json.loads(text)


def parse_llm_clips(llm_response: str) -> list:
    try:
        clips = _parse_llm_json(llm_response)
    except (json.JSONDecodeError, TypeError) as e:
        raise RuntimeError(
            'AI returned invalid response — try a different model'
        ) from e
    if not isinstance(clips, list) or len(clips) == 0:
        raise RuntimeError(
            'AI returned invalid response — try a different model'
        )
    return clips


def _call_lm_studio(prompt: str, model: str) -> list:
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.7,
        'stream': False,
    }

    url = f'{settings.LMSTUDIO_URL.rstrip("/")}/v1/chat/completions'
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except urllib.error.URLError:
        raise RuntimeError(
            'LM Studio not running. Start Server'
        ) from None
    except Exception as e:
        err = str(e)
        if 'LM Studio' in err or 'Connection refused' in err or '10061' in err:
            raise RuntimeError('LM Studio not running. Start Server') from e
        raise

    content = body['choices'][0]['message']['content']
    return parse_llm_clips(content)


def _cut_vertical(source: Path, output: Path, start: float, end: float):
    vf = (
        '[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,'
        'pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,boxblur=20:20[bg];'
        '[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];'
        '[bg][fg]overlay=(W-w)/2:(H-h)/2'
    )
    ffmpeg = str(resolve_ffmpeg())
    cmd = [
        ffmpeg, '-y',
        '-i', str(source),
        '-ss', str(start),
        '-to', str(end),
        '-filter_complex', vf,
        '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
        '-c:a', 'aac', '-b:a', '128k',
        str(output),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise RuntimeError(
            'FFmpeg not found. Install: winget install Gyan.FFmpeg '
            '(then restart Django), or set FFMPEG_PATH in settings.py'
        ) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.stderr or 'FFmpeg clip cutting failed') from e


def _render_clips(job_id: str, source: Path, clips: list):
    update_job(
        job_id,
        status='cutting',
        progress=0.65,
        message='Cutting and formatting vertical shorts…',
    )

    out_dir = _output_dir(job_id)
    n = max(len(clips), 1)

    for i, clip in enumerate(clips):
        short_id = f'short_{i + 1}'
        start = float(clip.get('start_time', 0))
        end = float(clip.get('end_time', start + 45))
        duration = round(end - start, 1)

        output_path = out_dir / f'{short_id}.mp4'
        _cut_vertical(source, output_path, start, end)

        short_meta = {
            'id': short_id,
            'title': clip.get('title', f'Short {i + 1}'),
            'hook': clip.get('hook', ''),
            'reason': clip.get('reason', ''),
            'start_time': start,
            'end_time': end,
            'duration': duration,
        }
        update_job(job_id, shorts=short_meta)

        progress = 0.65 + (0.35 * (i + 1) / n)
        update_job(
            job_id,
            progress=progress,
            message=f'Rendered short {i + 1} of {len(clips)}…',
        )

    update_job(
        job_id,
        status='done',
        progress=1.0,
        message='All shorts ready!',
    )


def run_pipeline(
    job_id: str,
    url: str,
    model: str,
    num_shorts: int,
    use_local_llm: bool = True,
    clip_start: float | None = None,
    clip_end: float | None = None,
):
    try:
        update_job(
            job_id,
            status='downloading',
            progress=0.05,
            message='Downloading video from YouTube…',
        )
        source = _download_video(job_id, url)
        job_dir = source.parent

        if clip_start is not None or clip_end is not None:
            update_job(
                job_id,
                message='Trimming video to selected time range…',
            )
            source = _trim_source(source, job_dir, clip_start, clip_end)

        update_job(
            job_id,
            status='transcribing',
            progress=0.25,
            message='Extracting audio and transcribing with Whisper…',
        )
        audio = _extract_audio(source, job_dir)
        transcript = _transcribe(audio)
        prompt = build_llm_prompt(transcript, num_shorts)

        if not use_local_llm:
            update_job(
                job_id,
                status='awaiting_llm',
                progress=0.50,
                message='Copy the prompt below, paste it into your LLM, then paste the JSON response back.',
                llm_prompt=prompt,
                transcript=transcript,
            )
            return

        update_job(
            job_id,
            status='analyzing',
            progress=0.50,
            message='Analyzing transcript with LM Studio…',
        )
        clips = _call_lm_studio(prompt, model)
        _render_clips(job_id, source, clips)

    except Exception as e:
        update_job(
            job_id,
            status='error',
            error=str(e),
            message='Something went wrong',
        )


def run_continue(job_id: str, llm_response: str):
    try:
        job_dir = _job_dir(job_id)
        source = _find_source_video(job_dir)

        update_job(
            job_id,
            status='analyzing',
            progress=0.55,
            message='Parsing your LLM response…',
            error=None,
        )
        clips = parse_llm_clips(llm_response)
        _render_clips(job_id, source, clips)

    except Exception as e:
        update_job(
            job_id,
            status='error',
            error=str(e),
            message='Something went wrong',
        )
