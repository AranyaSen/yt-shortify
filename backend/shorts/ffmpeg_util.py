import os
import shutil
import sys
from pathlib import Path

from django.conf import settings


def _winget_ffmpeg_candidates() -> list[Path]:
    if sys.platform != 'win32':
        return []
    packages = (
        Path(os.environ.get('LOCALAPPDATA', ''))
        / 'Microsoft'
        / 'WinGet'
        / 'Packages'
    )
    if not packages.is_dir():
        return []
    return sorted(packages.glob('Gyan.FFmpeg*/ffmpeg*/bin/ffmpeg.exe'))


def resolve_ffmpeg() -> Path:
    """Return path to ffmpeg executable, or raise RuntimeError with install hint."""
    configured = getattr(settings, 'FFMPEG_PATH', None) or os.environ.get('FFMPEG_PATH')
    if configured:
        path = Path(configured)
        if path.is_dir():
            path = path / ('ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg')
        if path.is_file():
            return path.resolve()

    found = shutil.which('ffmpeg')
    if found:
        return Path(found).resolve()

    for candidate in _winget_ffmpeg_candidates():
        if candidate.is_file():
            return candidate.resolve()

    for base in (
        Path(r'C:\ffmpeg\bin'),
        Path(os.environ.get('ProgramFiles', '')) / 'ffmpeg' / 'bin',
        Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'ffmpeg' / 'bin',
    ):
        exe = base / ('ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg')
        if exe.is_file():
            return exe.resolve()

    if sys.platform == 'win32':
        hint = (
            'FFmpeg not found. Install it, then restart your terminal:\n'
            '  winget install Gyan.FFmpeg\n'
            'Or add ffmpeg to PATH, or set FFMPEG_PATH in backend/config/settings.py'
        )
    else:
        hint = 'FFmpeg not found — install with: sudo apt install ffmpeg'
    raise RuntimeError(hint)


def ffmpeg_bin_dir() -> Path:
    return resolve_ffmpeg().parent
