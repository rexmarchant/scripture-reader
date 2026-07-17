#!/usr/bin/env python3
"""
ssml_generate.py — Phase 1.5 automation

Replaces ssml_converter.html. Reads a scripture chapter .txt file
(chapter title on the first line, blank-line-separated verses each
starting with "N " where N is the verse number) and writes two SSML
files next to it:

  {base}-v1.ssml   verse numbers stripped, <break time="300ms"/> per verse
                   -> paste into Amazon Polly (Neural, Brian voice)
  {base}-v2.ssml   verse numbers retained as "N. text"
                   -> input to vtt_align.py / verse alignment

Usage:
    python3 ssml_generate.py "Source Files/2 Nephi/16/2 Nep Ch 16 orig text.txt"

Naming convention matches the existing project files: spaces in the
input base name become underscores in the output filenames.
"""

import re
import sys
from pathlib import Path


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def parse_chapter(raw_text: str):
    """Split into (title, [(verse_num, verse_text), ...])."""
    # Normalize line endings, split on blank lines into paragraphs
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", normalized) if p.strip()]

    if not paragraphs:
        raise ValueError("No content found in source file")

    title = paragraphs[0].strip()
    verses = []
    verse_pat = re.compile(r"^(\d+)\s+(.*)$", re.DOTALL)

    for para in paragraphs[1:]:
        # Collapse internal newlines within a verse paragraph into single spaces
        para_flat = re.sub(r"\s*\n\s*", " ", para).strip()
        m = verse_pat.match(para_flat)
        if not m:
            raise ValueError(f"Could not parse verse number from paragraph: {para_flat[:80]!r}")
        num = int(m.group(1))
        text = m.group(2).strip()
        verses.append((num, text))

    if not verses:
        raise ValueError("No verses parsed after the title")

    # Sanity check: verse numbers should be sequential starting at 1
    expected = list(range(1, len(verses) + 1))
    actual = [v[0] for v in verses]
    if actual != expected:
        print(
            f"WARNING: verse numbers are not sequential 1..{len(verses)}. "
            f"Found: {actual}",
            file=sys.stderr,
        )

    return title, verses


def build_v1(title: str, verses) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<speak>", f"<p>{escape_xml(title)}</p>"]
    for _, text in verses:
        lines.append(f'<p>{escape_xml(text)}<break time="300ms"/></p>')
    lines.append("</speak>")
    return "\n".join(lines) + "\n"


def build_v2(title: str, verses) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<speak>", f"<p>{escape_xml(title)}</p>"]
    for num, text in verses:
        lines.append(f"<p>{num}. {escape_xml(text)}</p>")
    lines.append("</speak>")
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 ssml_generate.py <path-to-chapter.txt>", file=sys.stderr)
        sys.exit(1)

    src_path = Path(sys.argv[1])
    if not src_path.exists():
        print(f"File not found: {src_path}", file=sys.stderr)
        sys.exit(1)

    raw_text = src_path.read_text(encoding="utf-8", errors="replace")
    title, verses = parse_chapter(raw_text)

    base = src_path.stem.replace(" ", "_")
    out_dir = src_path.parent

    v1_path = out_dir / f"{base}-v1.ssml"
    v2_path = out_dir / f"{base}-v2.ssml"

    v1_path.write_text(build_v1(title, verses), encoding="utf-8")
    v2_path.write_text(build_v2(title, verses), encoding="utf-8")

    print(f"Title:  {title}")
    print(f"Verses: {len(verses)}")
    print(f"Wrote:  {v1_path}")
    print(f"Wrote:  {v2_path}")


if __name__ == "__main__":
    main()
