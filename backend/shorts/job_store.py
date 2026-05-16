import shutil
import threading
import time
import uuid
from datetime import datetime, timezone

from django.conf import settings

_lock = threading.Lock()
_jobs: dict[str, dict] = {}
_cleanup_started = False


def _now():
    return datetime.now(timezone.utc)


def create_job(**meta) -> str:
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            'job_id': job_id,
            'status': 'queued',
            'progress': 0.0,
            'message': 'Job queued',
            'shorts': [],
            'error': None,
            'llm_prompt': None,
            'transcript': None,
            'clip_start': meta.get('clip_start'),
            'clip_end': meta.get('clip_end'),
            'num_shorts': meta.get('num_shorts', 3),
            'use_local_llm': meta.get('use_local_llm', True),
            'render_mode': meta.get('render_mode', 'native'),
            'created_at': _now(),
            'thread': None,
        }
    return job_id


def get_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        return {
            'status': job['status'],
            'progress': job['progress'],
            'message': job['message'],
            'shorts': list(job['shorts']),
            'error': job['error'],
            'llm_prompt': job.get('llm_prompt'),
            'transcript': job.get('transcript'),
            'clip_start': job.get('clip_start'),
            'clip_end': job.get('clip_end'),
            'render_mode': job.get('render_mode', 'native'),
        }


def get_job_status(job_id: str) -> str | None:
    with _lock:
        job = _jobs.get(job_id)
        return job['status'] if job else None


def update_job(job_id: str, **kwargs):
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        for key, value in kwargs.items():
            if key == 'shorts':
                if isinstance(value, dict):
                    job['shorts'].append(value)
                elif isinstance(value, list):
                    job['shorts'] = value
            else:
                job[key] = value


def set_thread(job_id: str, thread: threading.Thread):
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job['thread'] = thread


def remove_job(job_id: str) -> bool:
    with _lock:
        if job_id not in _jobs:
            return False
        del _jobs[job_id]
        return True


def job_exists(job_id: str) -> bool:
    with _lock:
        return job_id in _jobs


def _cleanup_job_files(job_id: str):
    temp_path = settings.TEMP_DIR / job_id
    output_path = settings.OUTPUT_DIR / job_id
    if temp_path.exists():
        shutil.rmtree(temp_path, ignore_errors=True)
    if output_path.exists():
        shutil.rmtree(output_path, ignore_errors=True)


def cleanup_job(job_id: str):
    _cleanup_job_files(job_id)
    remove_job(job_id)


def _cleanup_loop():
    while True:
        time.sleep(300)
        cutoff = _now().timestamp() - settings.JOB_CLEANUP_SECONDS
        to_remove = []
        with _lock:
            for job_id, job in _jobs.items():
                if job['created_at'].timestamp() < cutoff:
                    to_remove.append(job_id)
        for job_id in to_remove:
            cleanup_job(job_id)


def start_cleanup_thread():
    global _cleanup_started
    if _cleanup_started:
        return
    _cleanup_started = True
    t = threading.Thread(target=_cleanup_loop, daemon=True)
    t.start()
