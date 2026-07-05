from app.validators import file_validator


def test_validate_mp4_file_when_extension_is_allowed(monkeypatch, tmp_path):
    mp4_file = tmp_path / "sample.mp4"
    mp4_file.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 32)

    monkeypatch.setattr(file_validator.settings, "ALLOWED_FILE_TYPES", {".pdf", ".mp4"})

    assert file_validator.validate_file_type(mp4_file, "sample.mp4") == "mp4"


def test_validate_html_file_when_extension_is_allowed(monkeypatch, tmp_path):
    html_file = tmp_path / "sample.html"
    html_file.write_text(
        "<!DOCTYPE html><html><head><title>Preview</title></head><body>Hello</body></html>",
        encoding="utf-8",
    )

    monkeypatch.setattr(file_validator.settings, "ALLOWED_FILE_TYPES", {".pdf", ".html"})

    assert file_validator.validate_file_type(html_file, "sample.html") == "html"
