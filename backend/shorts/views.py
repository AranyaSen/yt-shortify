import re
import threading

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from shorts import job_store
from shorts.pipeline import run_continue, run_pipeline

YOUTUBE_URL_RE = re.compile(
    r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)'
    r'[\w-]+',
    re.IGNORECASE,
)


def _parse_optional_float(value):
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_time_value(value):
    """Accept seconds (number) or mm:ss / hh:mm:ss strings."""
    if value is None or value == '':
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    if re.match(r'^\d+(\.\d+)?$', s):
        return float(s)
    parts = s.split(':')
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        return None
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return None


def _parse_render_mode(value) -> str:
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ('browser', 'wasm', 'client'):
            return 'browser'
        if v in ('native', 'server', 'ffmpeg'):
            return 'native'
    if value is False:
        return 'browser'
    if value is True:
        return 'native'
    return 'native'


class GenerateView(APIView):
    def post(self, request):
        url = (request.data.get('url') or '').strip()
        if not url or not YOUTUBE_URL_RE.match(url):
            return Response(
                {'error': 'Invalid YouTube URL'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        model = request.data.get('model') or settings.DEFAULT_MODEL
        num_shorts = request.data.get('num_shorts', 3)
        try:
            num_shorts = int(num_shorts)
            num_shorts = max(1, min(5, num_shorts))
        except (TypeError, ValueError):
            num_shorts = 3

        use_local_llm = request.data.get('use_local_llm', True)
        if isinstance(use_local_llm, str):
            use_local_llm = use_local_llm.lower() in ('true', '1', 'yes')

        clip_start = _parse_time_value(request.data.get('clip_start'))
        clip_end = _parse_time_value(request.data.get('clip_end'))

        if clip_start is not None and clip_end is not None and clip_end <= clip_start:
            return Response(
                {'error': 'End time must be after start time'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        render_mode = _parse_render_mode(request.data.get('render_mode', 'native'))

        job_id = job_store.create_job(
            clip_start=clip_start,
            clip_end=clip_end,
            num_shorts=num_shorts,
            use_local_llm=use_local_llm,
            render_mode=render_mode,
        )

        thread = threading.Thread(
            target=run_pipeline,
            kwargs={
                'job_id': job_id,
                'url': url,
                'model': model,
                'num_shorts': num_shorts,
                'use_local_llm': use_local_llm,
                'clip_start': clip_start,
                'clip_end': clip_end,
            },
            daemon=True,
        )
        job_store.set_thread(job_id, thread)
        thread.start()

        return Response({'job_id': job_id}, status=status.HTTP_201_CREATED)


class ContinueView(APIView):
    def post(self, request, job_id):
        if not job_store.job_exists(job_id):
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        current = job_store.get_job_status(job_id)
        if current != 'awaiting_llm':
            return Response(
                {'error': f'Job is not waiting for LLM response (status: {current})'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        llm_response = (request.data.get('llm_response') or '').strip()
        if not llm_response:
            return Response(
                {'error': 'llm_response is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job_store.update_job(
            job_id,
            status='analyzing',
            progress=0.55,
            message='Parsing your LLM response…',
            error=None,
        )

        thread = threading.Thread(
            target=run_continue,
            args=(job_id, llm_response),
            daemon=True,
        )
        job_store.set_thread(job_id, thread)
        thread.start()

        return Response({'ok': True}, status=status.HTTP_202_ACCEPTED)


class StatusView(APIView):
    def get(self, request, job_id):
        job = job_store.get_job(job_id)
        if job is None:
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(job)


class SegmentView(APIView):
    def get(self, request, job_id, short_id):
        if not re.match(r'^short_\d+$', short_id):
            raise Http404('Invalid short id')

        if not job_store.job_exists(job_id):
            raise Http404('Job not found')

        path = settings.TEMP_DIR / job_id / 'segments' / f'{short_id}.mp4'
        if not path.exists():
            raise Http404('Segment not found')

        return FileResponse(
            open(path, 'rb'),
            content_type='video/mp4',
            as_attachment=False,
        )


class SourceView(APIView):
    def get(self, request, job_id):
        if not job_store.job_exists(job_id):
            raise Http404('Job not found')

        job_dir = settings.TEMP_DIR / job_id
        if not job_dir.exists():
            raise Http404('Source video not found')

        for name in ('source.mp4', 'source.mkv', 'source.webm'):
            path = job_dir / name
            if path.exists():
                return FileResponse(
                    open(path, 'rb'),
                    content_type='video/mp4',
                    as_attachment=False,
                )

        for f in job_dir.iterdir():
            if f.suffix.lower() in ('.mp4', '.mkv', '.webm', '.mov'):
                return FileResponse(
                    open(f, 'rb'),
                    content_type='video/mp4',
                    as_attachment=False,
                )

        raise Http404('Source video not found')


class RenderCompleteView(APIView):
    def post(self, request, job_id):
        if not job_store.job_exists(job_id):
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        current = job_store.get_job_status(job_id)
        job = job_store.get_job(job_id)
        if job and job.get('render_mode') != 'browser':
            return Response(
                {'error': 'Render complete is only for browser rendering mode'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if current not in ('ready_to_render', 'rendering', 'extracting_segments'):
            return Response(
                {'error': f'Job is not ready to finalize (status: {current})'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job_store.update_job(
            job_id,
            status='done',
            progress=1.0,
            message='All shorts ready!',
        )
        return Response({'ok': True})


class DownloadView(APIView):
    def get(self, request, job_id, short_id):
        if not re.match(r'^short_\d+$', short_id):
            raise Http404('Invalid short id')

        path = settings.OUTPUT_DIR / job_id / f'{short_id}.mp4'
        if not path.exists():
            raise Http404('Short not found')

        return FileResponse(
            open(path, 'rb'),
            content_type='application/octet-stream',
            as_attachment=False,
            filename=f'{short_id}.mp4',
        )


class CleanupView(APIView):
    def delete(self, request, job_id):
        if not job_store.job_exists(job_id):
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        job_store.cleanup_job(job_id)
        return Response({'ok': True})
