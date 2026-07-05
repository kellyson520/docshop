from types import SimpleNamespace

from app.services.media_metadata_service import (
    extract_video_metadata,
    extract_video_poster_frame,
    generate_compatible_video_preview,
    summarize_media_metadata,
)


def test_summarize_media_metadata_normalizes_video_fields():
    summary = summarize_media_metadata(
        {
            "duration": 30.5,
            "width": 1920,
            "height": 1080,
            "codec": "h264",
            "bit_rate": 128000,
        }
    )

    assert summary["duration_seconds"] == 30.5
    assert summary["dimensions"] == {"width": 1920, "height": 1080}
    assert summary["codec"] == "h264"
    assert summary["bit_rate"] == 128000


def test_summarize_media_metadata_normalizes_image_fields():
    summary = summarize_media_metadata(
        {
            "width": 3024,
            "height": 4032,
            "format": "jpeg",
            "mode": "RGBA",
            "orientation": 6,
            "has_alpha": True,
        }
    )

    assert summary["dimensions"] == {"width": 3024, "height": 4032}
    assert summary["format"] == "JPEG"
    assert summary["color_mode"] == "RGBA"
    assert summary["has_alpha"] is True
    assert summary["orientation"] == 6
    assert summary["aspect_ratio"] == "3:4"


def test_summarize_media_metadata_derives_alpha_from_color_mode():
    summary = summarize_media_metadata(
        {
            "width": 1200,
            "height": 800,
            "format": "png",
            "mode": "LA",
        }
    )

    assert summary["color_mode"] == "LA"
    assert summary["has_alpha"] is True


def test_extract_video_poster_frame_uses_ffmpeg_when_available(monkeypatch, tmp_path):
    import app.services.media_metadata_service as media_metadata_service

    source = tmp_path / "demo.mp4"
    source.write_bytes(b"video")
    poster = tmp_path / "poster.jpg"
    calls = []

    def fake_run(args, capture_output, timeout, check):
        calls.append(args)
        poster.write_bytes(b"poster")
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(media_metadata_service, "_find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(media_metadata_service.subprocess, "run", fake_run)

    result = extract_video_poster_frame(str(source), str(poster))

    assert result == {
        "path": str(poster),
        "generated": True,
    }
    assert calls
    assert calls[0][0] == "ffmpeg"
    assert calls[0][-1] == str(poster)


def test_generate_compatible_video_preview_uses_ffmpeg_when_available(monkeypatch, tmp_path):
    import app.services.media_metadata_service as media_metadata_service

    source = tmp_path / "demo.mov"
    source.write_bytes(b"video")
    output = tmp_path / "preview-video.mp4"
    calls = []

    def fake_run(args, capture_output, timeout, check):
        calls.append(args)
        output.write_bytes(b"preview-video")
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(media_metadata_service, "_find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(media_metadata_service.subprocess, "run", fake_run)

    result = generate_compatible_video_preview(str(source), str(output))

    assert result == {
        "path": str(output),
        "generated": True,
    }
    assert calls
    assert calls[0][0] == "ffmpeg"
    assert calls[0][-1] == str(output)


def test_extract_video_metadata_uses_ffprobe_when_available(monkeypatch, tmp_path):
    import json
    import app.services.media_metadata_service as media_metadata_service

    source = tmp_path / "demo.mp4"
    source.write_bytes(b"video")
    calls = []

    def fake_run(args, capture_output, timeout, check, text):
        calls.append(args)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "streams": [
                        {
                            "codec_type": "video",
                            "codec_name": "h264",
                            "width": 1280,
                            "height": 720,
                            "bit_rate": "256000",
                            "duration": "12.5",
                        }
                    ],
                    "format": {
                        "duration": "12.5",
                        "bit_rate": "512000",
                        "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                    },
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(media_metadata_service, "_find_ffprobe", lambda: "ffprobe", raising=False)
    monkeypatch.setattr(media_metadata_service.subprocess, "run", fake_run)

    result = extract_video_metadata(str(source))

    assert result == {
        "duration_seconds": 12.5,
        "dimensions": {"width": 1280, "height": 720},
        "codec": "h264",
        "bit_rate": 256000,
        "format": "MP4",
        "color_mode": None,
        "has_alpha": None,
        "orientation": None,
        "aspect_ratio": "16:9",
    }
    assert calls
    assert calls[0][0] == "ffprobe"
    assert calls[0][-1] == str(source)
