from __future__ import annotations

import json
from math import gcd
from pathlib import Path
import shutil
import subprocess

from PIL import Image


_ALPHA_MODES = {"RGBA", "LA", "PA"}
_ORIENTATION_EXIF_TAG = 274


def _normalize_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_text(value, *, upper: bool = False) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.upper() if upper else text


def _normalize_bool(value) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y"}:
            return True
        if lowered in {"0", "false", "no", "n"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def _infer_has_alpha(color_mode: str | None, raw_value) -> bool | None:
    normalized = _normalize_bool(raw_value)
    if normalized is not None:
        return normalized
    if not color_mode:
        return None
    return color_mode.upper() in _ALPHA_MODES or "A" in color_mode.upper()


def _aspect_ratio(width: int | None, height: int | None) -> str | None:
    if not width or not height:
        return None
    divisor = gcd(abs(width), abs(height)) or 1
    return f"{abs(width) // divisor}:{abs(height) // divisor}"


def summarize_media_metadata(metadata: dict | None) -> dict:
    metadata = metadata or {}
    width = _normalize_int(metadata.get("width"))
    height = _normalize_int(metadata.get("height"))
    color_mode = _normalize_text(metadata.get("color_mode") or metadata.get("mode"), upper=True)
    format_name = _normalize_text(metadata.get("format"), upper=True)
    summary = {
        "duration_seconds": _normalize_float(metadata.get("duration")),
        "dimensions": {
            "width": width,
            "height": height,
        },
        "codec": _normalize_text(metadata.get("codec")),
        "bit_rate": _normalize_int(metadata.get("bit_rate")),
        "format": format_name,
        "color_mode": color_mode,
        "has_alpha": _infer_has_alpha(color_mode, metadata.get("has_alpha")),
        "orientation": _normalize_int(metadata.get("orientation")),
        "aspect_ratio": _aspect_ratio(width, height),
    }
    return summary


def extract_image_metadata(file_path: str) -> dict:
    fallback_format = _normalize_text(Path(file_path).suffix.lstrip("."), upper=True)
    try:
        with Image.open(file_path) as image:
            exif = image.getexif() or {}
            return summarize_media_metadata(
                {
                    "width": image.width,
                    "height": image.height,
                    "format": image.format or fallback_format,
                    "mode": image.mode,
                    "has_alpha": ("A" in image.getbands()) or ("transparency" in image.info),
                    "orientation": exif.get(_ORIENTATION_EXIF_TAG),
                }
            )
    except Exception:
        return summarize_media_metadata({"format": fallback_format})


def _find_ffprobe() -> str | None:
    return shutil.which("ffprobe")


def _find_ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def _normalize_video_format(format_name: str | None, fallback_format: str | None) -> str | None:
    if fallback_format:
        return fallback_format
    normalized = _normalize_text(format_name)
    if not normalized:
        return None
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    return parts[0].upper() if parts else None


def extract_video_metadata(file_path: str) -> dict:
    fallback_format = _normalize_text(Path(file_path).suffix.lstrip("."), upper=True)
    ffprobe = _find_ffprobe()
    if not ffprobe:
        return summarize_media_metadata({"format": fallback_format})

    try:
        completed = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                str(file_path),
            ],
            capture_output=True,
            timeout=30,
            check=False,
            text=True,
        )
    except Exception:
        return summarize_media_metadata({"format": fallback_format})

    if completed.returncode != 0 or not completed.stdout:
        return summarize_media_metadata({"format": fallback_format})

    try:
        payload = json.loads(completed.stdout)
    except (TypeError, ValueError, json.JSONDecodeError):
        return summarize_media_metadata({"format": fallback_format})

    streams = payload.get("streams") or []
    format_info = payload.get("format") or {}
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if video_stream is None and streams:
        video_stream = streams[0]
    video_stream = video_stream or {}

    return summarize_media_metadata(
        {
            "duration": video_stream.get("duration") or format_info.get("duration"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "codec": video_stream.get("codec_name"),
            "bit_rate": video_stream.get("bit_rate") or format_info.get("bit_rate"),
            "format": _normalize_video_format(format_info.get("format_name"), fallback_format),
        }
    )


def extract_video_poster_frame(file_path: str, output_path: str) -> dict:
    ffmpeg = _find_ffmpeg()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if not ffmpeg:
        return {"path": str(output), "generated": False}

    try:
        completed = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-ss",
                "00:00:00.000",
                "-i",
                str(file_path),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(output),
            ],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except Exception:
        return {"path": str(output), "generated": False}

    generated = completed.returncode == 0 and output.exists() and output.stat().st_size > 0
    return {"path": str(output), "generated": generated}


def generate_compatible_video_preview(file_path: str, output_path: str) -> dict:
    ffmpeg = _find_ffmpeg()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if not ffmpeg:
        return {"path": str(output), "generated": False}

    try:
        completed = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(file_path),
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-vf",
                "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
                "-movflags",
                "+faststart",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(output),
            ],
            capture_output=True,
            timeout=120,
            check=False,
        )
    except Exception:
        return {"path": str(output), "generated": False}

    generated = completed.returncode == 0 and output.exists() and output.stat().st_size > 0
    return {"path": str(output), "generated": generated}
