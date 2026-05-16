import json
import re
import urllib.error
import urllib.request
from pathlib import Path

import yt_dlp
from django.conf import settings
from faster_whisper import WhisperModel

from shorts import job_store
from shorts.segment_util import extract_segment, render_vertical_short


def update_job(job_id: str, **kwargs):
    job_store.update_job(job_id, **kwargs)


def _job_dir(job_id: str) -> Path:
    d = settings.TEMP_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _find_source_video(job_dir: Path) -> Path:
    for name in ('source.mp4', 'source.mkv', 'source.webm'):
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

    ydl_opts = {
        'format': (
            'best[ext=mp4][vcodec^=avc1]/best[ext=mp4]/'
            'best[height<=1080][ext=mp4]/best'
        ),
        'outtmpl': out_template,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        raise RuntimeError(str(e)) from e

    return _find_source_video(job_dir)


def _clip_timestamps_arg(
    clip_start: float | None,
    clip_end: float | None,
) -> str | None:
    if clip_start is None and clip_end is None:
        return None
    start = float(clip_start or 0)
    if clip_end is not None:
        return f'{start},{float(clip_end)}'
    return f'{start},'


def _transcribe(
    source: Path,
    clip_start: float | None = None,
    clip_end: float | None = None,
) -> str:
    try:
        model = WhisperModel(
            settings.WHISPER_MODEL_SIZE,
            device='cpu',
            compute_type='int8',
        )
        kwargs = {}
        clip_ts = _clip_timestamps_arg(clip_start, clip_end)
        if clip_ts:
            kwargs['clip_timestamps'] = clip_ts

        segments, _ = model.transcribe(str(source), **kwargs)
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


def _output_dir(job_id: str) -> Path:
    d = settings.OUTPUT_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _segments_dir(job_id: str) -> Path:
    d = _job_dir(job_id) / 'segments'
    d.mkdir(parents=True, exist_ok=True)
    return d


def _time_offset(job_id: str) -> float:
    job = job_store.get_job(job_id)
    if job and job.get('clip_start') is not None:
        return float(job['clip_start'])
    return 0.0


def _build_shorts_meta(clips: list, time_offset: float) -> list:
    shorts_meta = []
    for i, clip in enumerate(clips):
        short_id = f'short_{i + 1}'
        rel_start = float(clip.get('start_time', 0))
        rel_end = float(clip.get('end_time', rel_start + 45))
        start = rel_start + time_offset
        end = rel_end + time_offset
        duration = round(end - start, 1)
        shorts_meta.append({
            'id': short_id,
            'title': clip.get('title', f'Short {i + 1}'),
            'hook': clip.get('hook', ''),
            'reason': clip.get('reason', ''),
            'start_time': start,
            'end_time': end,
            'duration': duration,
        })
    return shorts_meta


def _render_mode(job_id: str) -> str:
    job = job_store.get_job(job_id)
    return (job or {}).get('render_mode', 'native')


def finish_rendering(job_id: str, clips: list):
    if _render_mode(job_id) == 'browser':
        _prepare_client_render(job_id, clips)
    else:
        _render_native(job_id, clips)


def _render_native(job_id: str, clips: list):
    time_offset = _time_offset(job_id)
    shorts_meta = _build_shorts_meta(clips, time_offset)
    source = _find_source_video(_job_dir(job_id))
    out_dir = _output_dir(job_id)
    n = max(len(shorts_meta), 1)

    update_job(
        job_id,
        status='cutting',
        progress=0.65,
        message='Rendering vertical shorts with native FFmpeg…',
        shorts=[],
    )

    for i, meta in enumerate(shorts_meta):
        output_path = out_dir / f'{meta["id"]}.mp4'
        render_vertical_short(
            source,
            output_path,
            meta['start_time'],
            meta['end_time'],
        )
        update_job(job_id, shorts=meta)
        update_job(
            job_id,
            progress=0.65 + (0.35 * (i + 1) / n),
            message=f'Rendered short {i + 1} of {len(shorts_meta)}…',
        )

    update_job(
        job_id,
        status='done',
        progress=1.0,
        message='All shorts ready!',
    )


def _prepare_client_render(job_id: str, clips: list):
    time_offset = _time_offset(job_id)
    shorts_meta = _build_shorts_meta(clips, time_offset)
    source = _find_source_video(_job_dir(job_id))
    seg_dir = _segments_dir(job_id)
    n = max(len(shorts_meta), 1)

    update_job(
        job_id,
        status='extracting_segments',
        progress=0.60,
        message='Cutting short segments from source video…',
    )

    for i, meta in enumerate(shorts_meta):
        seg_path = seg_dir / f'{meta["id"]}.mp4'
        extract_segment(source, seg_path, meta['start_time'], meta['end_time'])
        update_job(
            job_id,
            progress=0.60 + (0.05 * (i + 1) / n),
            message=f'Prepared segment {i + 1} of {len(shorts_meta)}…',
        )

    update_job(
        job_id,
        status='ready_to_render',
        progress=0.65,
        message='Formatting vertical shorts in your browser…',
        shorts=shorts_meta,
        time_offset=time_offset,
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

        update_job(
            job_id,
            status='transcribing',
            progress=0.25,
            message='Transcribing audio with Whisper…',
        )
        transcript = _transcribe(source, clip_start, clip_end)
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
        finish_rendering(job_id, clips)

    except Exception as e:
        update_job(
            job_id,
            status='error',
            error=str(e),
            message='Something went wrong',
        )


def run_continue(job_id: str, llm_response: str):
    try:
        update_job(
            job_id,
            status='analyzing',
            progress=0.55,
            message='Parsing your LLM response…',
            error=None,
        )
        clips = parse_llm_clips(llm_response)
        finish_rendering(job_id, clips)

    except Exception as e:
        update_job(
            job_id,
            status='error',
            error=str(e),
            message='Something went wrong',
        )
