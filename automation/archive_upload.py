#!/usr/bin/env python3
"""
archive_upload.py -- Phase 3 automation

Replaces the manual Archive.org upload: log in, drag the mp3, fill out
metadata, wait for the item page, copy the /download/ link. This uploads
via Archive.org's S3-like API (through the `internetarchive` package) and
prints the direct /download/ URL needed for Phase 4.

Metadata follows the project's fixed convention:
    Title:       "{Book} Ch {N}"
    Description: "{Scripture Set}, {Book} Ch {N} AI Voice"
    Tags:        "Scripture Set, {Book} Chapter {N}"

Requires:
    pip install internetarchive --break-system-packages
    Archive.org S3-like API keys (from https://archive.org/account/s3.php):
        export IA_ACCESS_KEY=...
        export IA_SECRET_KEY=...

Usage:
    python3 archive_upload.py chapter.mp3 --book "2 Nephi" --chapter-num 16 \\
        --scripture-set "Book of Mormon"

    # Optionally override the item identifier (defaults to a slug derived
    # from book + chapter number, matching the project's existing convention
    # e.g. "2-nephi-ch-16"):
    python3 archive_upload.py chapter.mp3 --book "2 Nephi" --chapter-num 16 \\
        --identifier 2-nephi-ch-16
"""

import argparse
import os
import re
import sys
import urllib.parse
from pathlib import Path


def default_identifier(book: str, chapter_num: str) -> str:
    slug = f"{book}-ch-{chapter_num}".lower()
    return re.sub(r"[^a-z0-9]+", "-", slug).strip("-")


def main():
    ap = argparse.ArgumentParser(description="Upload a chapter mp3 to Archive.org and print its /download/ URL.")
    ap.add_argument("mp3_file")
    ap.add_argument("--book", required=True, help='e.g. "2 Nephi"')
    ap.add_argument("--chapter-num", required=True, help='e.g. "16"')
    ap.add_argument("--scripture-set", default="Book of Mormon")
    ap.add_argument("--identifier", help="Archive.org item identifier (defaults to a slug like 2-nephi-ch-16)")
    ap.add_argument("--voice-label", default="AI Voice", help="Suffix used in the description, e.g. 'AI Voice'")
    args = ap.parse_args()

    try:
        import internetarchive as ia
    except ImportError:
        print("ERROR: internetarchive package not installed. Run: pip install internetarchive --break-system-packages", file=sys.stderr)
        sys.exit(1)

    access_key = os.environ.get("IA_ACCESS_KEY")
    secret_key = os.environ.get("IA_SECRET_KEY")
    if not access_key or not secret_key:
        print(
            "ERROR: Set IA_ACCESS_KEY and IA_SECRET_KEY environment variables.\n"
            "Get them from https://archive.org/account/s3.php",
            file=sys.stderr,
        )
        sys.exit(1)

    mp3_path = Path(args.mp3_file)
    if not mp3_path.exists():
        print(f"ERROR: File not found: {mp3_path}", file=sys.stderr)
        sys.exit(1)

    identifier = args.identifier or default_identifier(args.book, args.chapter_num)
    title = f"{args.book} Ch {args.chapter_num}"
    description = f"{args.scripture_set}, {args.book} Ch {args.chapter_num} {args.voice_label}"
    tags = f"{args.scripture_set}, {args.book} Chapter {args.chapter_num}"

    metadata = {
        "title": title,
        "description": description,
        "subject": tags,
        "mediatype": "audio",
        "collection": "opensource_audio",
    }

    print(f"Uploading {mp3_path.name} to archive.org/details/{identifier} ...")
    result = ia.upload(
        identifier,
        files=[str(mp3_path)],
        metadata=metadata,
        access_key=access_key,
        secret_key=secret_key,
        verbose=True,
    )

    ok = all(r.status_code in (200, None) for r in result if hasattr(r, "status_code"))
    if not ok:
        print("ERROR: Upload did not complete successfully -- check output above.", file=sys.stderr)
        sys.exit(1)

    encoded_filename = urllib.parse.quote(mp3_path.name)
    download_url = f"https://archive.org/download/{identifier}/{encoded_filename}"

    print("\nUpload complete.")
    print(f"Item page:    https://archive.org/details/{identifier}")
    print(f"Download URL: {download_url}")
    print("\n(This is the URL to pass as --audio-url to chapter_export.py)")


if __name__ == "__main__":
    main()
