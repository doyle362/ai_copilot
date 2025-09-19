import base64
from pathlib import Path

import pytest

from services.analyst.analyst.utils.attachments import normalize_attachments


@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAA" "AAC0lEQVR42mP8/x8AAukB9p2Zci4AAAAASUVORK5CYII="
    )
    path = tmp_path / "pixel.png"
    path.write_bytes(data)
    return path


def test_image_attachment_converted_to_image_url(sample_png: Path) -> None:
    attachments, diagnostics = normalize_attachments([sample_png])

    assert attachments[0]["type"] == "image_url"
    image_payload = attachments[0]["image_url"]
    assert image_payload["url"].startswith("data:image/png;base64,")
    assert "pixel.png" in image_payload["filename"]
    assert diagnostics[0].startswith("Attached image:")


def test_non_image_converted_to_text_note(tmp_path: Path) -> None:
    text_file = tmp_path / "notes.pub"
    text_file.write_text("Parking updates go here.")

    attachments, diagnostics = normalize_attachments([text_file])

    assert attachments[0]["type"] == "text_note"
    assert "Parking updates" in attachments[0]["text"]
    assert attachments[0]["metadata"]["reason"] == "non-image"
    assert diagnostics[0].startswith("Converted attachment to text note")


def test_no_images_flag_downgrades_images(sample_png: Path) -> None:
    attachments, _ = normalize_attachments([sample_png], allow_images=False)

    assert attachments[0]["type"] == "text_note"
    assert attachments[0]["metadata"]["reason"] == "images disabled"


def test_missing_attachment_produces_note(tmp_path: Path) -> None:
    missing = tmp_path / "missing.png"

    attachments, diagnostics = normalize_attachments([missing])

    assert attachments[0]["type"] == "text_note"
    assert attachments[0]["metadata"]["reason"] == "missing"
    assert diagnostics[0].startswith("Attachment missing")
