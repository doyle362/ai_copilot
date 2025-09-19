#!/usr/bin/env python3
"""Utility CLI that prepares Codex chat payloads with safe attachment handling."""

from __future__ import annotations

import argparse
import json
from typing import List

import sys
import os

# Add the services/analyst directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "services", "analyst"))

from analyst.utils.attachments import normalize_attachments


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a chat payload with optional attachments, normalising files "
            "so that only real images are uploaded as image_url entries."
        )
    )
    parser.add_argument(
        "--message",
        "-m",
        required=True,
        help="User message to send to the Codex runner.",
    )
    parser.add_argument(
        "--attachment",
        "-a",
        action="append",
        default=[],
        metavar="PATH",
        help="Attachment to include. Repeat for multiple files.",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip embedding images; attachments will be converted to text notes.",
    )
    parser.add_argument(
        "--text-preview-chars",
        type=int,
        default=600,
        help=(
            "Maximum number of characters to include from text attachments when "
            "creating notes (default: 600). Use 0 to disable excerpts."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    attachments: List[str] = args.attachment
    normalised, diagnostics = normalize_attachments(
        attachments,
        allow_images=not args.no_images,
        text_preview_chars=args.text_preview_chars,
    )

    payload = {
        "message": args.message,
        "attachments": normalised,
        "diagnostics": diagnostics,
    }

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
