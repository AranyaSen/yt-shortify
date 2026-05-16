import subprocess
from pathlib import Path


def _ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def extract_segment(source: Path, dest: Path, start: float, end: float) -> None:
    """Cut a time range from the source into a small MP4 (stream copy when possible)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.1, float(end) - float(start))
    ffmpeg = _ffmpeg_exe()

    copy_cmd = [
        ffmpeg,
        '-y',
        '-ss',
        str(start),
        '-i',
        str(source),
        '-t',
        str(duration),
        '-map',
        '0:v:0?',
        '-map',
        '0:a:0?',
        '-c',
        'copy',
        '-avoid_negative_ts',
        'make_zero',
        '-movflags',
        '+faststart',
        str(dest),
    ]

    try:
        subprocess.run(copy_cmd, check=True, capture_output=True, text=True)
        return
    except subprocess.CalledProcessError:
        pass

    encode_cmd = [
        ffmpeg,
        '-y',
        '-ss',
        str(start),
        '-i',
        str(source),
        '-t',
        str(duration),
        '-map',
        '0:v:0?',
        '-map',
        '0:a:0?',
        '-c:v',
        'libx264',
        '-preset',
        'ultrafast',
        '-crf',
        '28',
        '-c:a',
        'aac',
        '-b:a',
        '128k',
        '-movflags',
        '+faststart',
        str(dest),
    ]
    try:
        subprocess.run(encode_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.stderr or 'Failed to extract video segment') from e


VERTICAL_FILTER = (
    '[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,'
    'pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1'
)


def render_vertical_short(
    source: Path,
    output: Path,
    start: float,
    end: float,
) -> None:
    """Cut and format a vertical 1080x1920 short with bundled native FFmpeg."""
    output.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.1, float(end) - float(start))
    ffmpeg = _ffmpeg_exe()

    cmd = [
        ffmpeg,
        '-y',
        '-ss',
        str(start),
        '-i',
        str(source),
        '-t',
        str(duration),
        '-vf',
        VERTICAL_FILTER,
        '-c:v',
        'libx264',
        '-preset',
        'fast',
        '-crf',
        '23',
        '-pix_fmt',
        'yuv420p',
        '-c:a',
        'aac',
        '-b:a',
        '128k',
        '-movflags',
        '+faststart',
        str(output),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.stderr or 'Native FFmpeg render failed') from e
