"""Attachment normalization helpers for Codex/CLI workflows.

This module guards downstream API calls from invalid attachment payloads by
ensuring that only genuine images are encoded as `image_url` objects. All other
attachments are converted into lightweight text notes so that requests no
longer fail when non-image files are present.
"""

from __future__ import annotations

import base64
import imghdr
import mimetypes
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

AttachmentInput = Union[str, Path]
NormalizedAttachment = Dict[str, Any]
__all__ = ["normalize_attachments"]

# Maximum number of characters to keep when creating a text excerpt for a
# non-image attachment.
_DEFAULT_TEXT_PREVIEW_CHARS = 600


def normalize_attachments(
    attachments: Iterable[AttachmentInput],
    *,
    allow_images: bool = True,
    text_preview_chars: int = _DEFAULT_TEXT_PREVIEW_CHARS,
) -> Tuple[List[NormalizedAttachment], List[str]]:
    """Normalise attachments for API consumption.

    Parameters
    ----------
    attachments:
        Iterable of filesystem paths (``str`` or ``Path``) pointing to potential
        attachments.
    allow_images:
        When ``True`` (default) real image files are converted to ``image_url``
        payloads. When ``False`` images are treated like any other attachment and
        emitted as text notes.
    text_preview_chars:
        Maximum number of characters to include when embedding a text excerpt
        inside a text note. A value of ``0`` disables excerpt extraction.

    Returns
    -------
    Tuple[List[NormalizedAttachment], List[str]]
        The first item is the list of normalised attachment payloads. The second
        item contains diagnostic strings that can be surfaced to the caller (for
        example, to show which attachments were downgraded to text notes).
    """

    normalised: List[NormalizedAttachment] = []
    diagnostics: List[str] = []

    for raw in attachments:
        path = Path(raw).expanduser() if isinstance(raw, (str, Path)) else None
        if path is None:
            continue

        if not path.exists():
            note = _build_missing_note(path)
            normalised.append(note)
            diagnostics.append(f"Attachment missing: {path}")
            continue

        mime_type = _guess_mime_type(path)
        is_image = _is_real_image(path, mime_type)

        if allow_images and is_image:
            try:
                payload = _build_image_payload(path, mime_type)
                normalised.append(payload)
                diagnostics.append(f"Attached image: {path.name} ({mime_type})")
            except Exception as exc:  # noqa: BLE001
                # If encoding fails we still want to proceed with a text note so
                # the request does not crash.
                note = _build_error_note(path, f"Failed to encode image: {exc}")
                normalised.append(note)
                diagnostics.append(f"Failed to encode image {path}: {exc}")
        else:
            reason = "images disabled" if is_image else "non-image"
            note = _build_text_note(
                path,
                reason=reason,
                mime_type=mime_type,
                excerpt=_read_text_excerpt(path, text_preview_chars),
            )
            normalised.append(note)
            diagnostics.append(
                f"Converted attachment to text note: {path.name} ({reason})"
            )

    return normalised, diagnostics


def _guess_mime_type(path: Path) -> Optional[str]:
    mime_type, _ = mimetypes.guess_type(path.as_posix())
    return mime_type


def _is_real_image(path: Path, mime_type: Optional[str]) -> bool:
    if mime_type and mime_type.startswith("image/"):
        detected = imghdr.what(path)
        return detected is not None
    # Fall back to imghdr for files without a known extension.
    detected = imghdr.what(path)
    return detected is not None


def _build_image_payload(path: Path, mime_type: Optional[str]) -> NormalizedAttachment:
    data = path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    resolved_mime = mime_type or "image/unknown"
    data_url = f"data:{resolved_mime};base64,{encoded}"

    return {
        "type": "image_url",
        "image_url": {
            "url": data_url,
            "detail": "auto",
            "mime_type": resolved_mime,
            "filename": path.name,
        },
    }


def _build_text_note(
    path: Path,
    *,
    reason: str,
    mime_type: Optional[str],
    excerpt: Optional[str],
) -> NormalizedAttachment:
    lines = [f"[Attachment: {path.name} — {reason}]"]
    if mime_type:
        lines.append(f"MIME type: {mime_type}")
    if excerpt:
        lines.append("")
        lines.append(excerpt)

    text = "\n".join(lines)

    return {
        "type": "text_note",
        "text": text,
        "metadata": {
            "source": str(path),
            "reason": reason,
            "mime_type": mime_type,
        },
    }


def _build_missing_note(path: Path) -> NormalizedAttachment:
    return {
        "type": "text_note",
        "text": f"[Attachment missing: {path.name}] {path}",
        "metadata": {
            "source": str(path),
            "reason": "missing",
            "mime_type": None,
        },
    }


def _build_error_note(path: Path, error: str) -> NormalizedAttachment:
    return {
        "type": "text_note",
        "text": f"[Attachment error: {path.name}] {error}",
        "metadata": {
            "source": str(path),
            "reason": "error",
            "mime_type": _guess_mime_type(path),
        },
    }


def _read_text_excerpt(path: Path, text_preview_chars: int) -> Optional[str]:
    if text_preview_chars <= 0:
        return None

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    except Exception:
        return None

    if len(text) <= text_preview_chars:
        return text

    truncated = text[:text_preview_chars].rstrip()
    return f"{truncated}…"
