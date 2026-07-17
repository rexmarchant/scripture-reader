#!/usr/bin/env python3
"""
chapter_export.py -- Phase 4 automation

Replaces the manual "Export Chapter Player" step in audio_sync_player.html.
Given a verse-aligned VTT (from vtt_align.py), the chapter's metadata, and
the Archive.org MP3 URL, this:

  1. Generates chapterfiles/{slug}.html (same template the browser tool wrote)
  2. Upserts the chapter into a persistent site/library.json (replaces the
     browser's localStorage-based library, since we have no browser here)
  3. Regenerates site/index.html from the full library (same 3-level
     Scripture Set -> Book -> Chapter layout, same canonical book sort order
     ported from scripture_reader.html's sortChapters())
  4. Appends a row to scripture_export_log.csv

Usage:
    python3 chapter_export.py \\
        --site "Scripture Reader-WORKING/site" \\
        --vtt "Source Files/2 Nephi/16/2_Nep_Ch_16_Final-vtt.vtt" \\
        --scripture-set "Book of Mormon" --book "2 Nephi" --chapter "Chapter 16" \\
        --audio-url "https://archive.org/download/2-nephi-ch-16/2%20Nephi%20Ch%2016.mp3" \\
        --mp3 "Source Files/2 Nephi/16/2 Nephi Ch 16.mp3" \\
        --log "scripture_export_log.csv"

On first run (no library.json yet), the library is bootstrapped by scanning
the existing site/chapterfiles/*.html for their embedded CHAPTER_DATA.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vtt_align import parse_vtt  # reuse the same WEBVTT cue parser


BOOK_ORDER = {
    "Book of Mormon": [
        "1 Nephi", "2 Nephi", "Jacob", "Enos", "Jarom", "Omni", "Words of Mormon",
        "Mosiah", "Alma", "Helaman", "3 Nephi", "4 Nephi", "Mormon", "Ether", "Moroni",
    ],
    "Doctrine and Covenants": [],
    "Pearl of Great Price": [
        "Moses", "Abraham", "Joseph Smith--Matthew", "Joseph Smith--History",
        "Articles of Faith",
    ],
    "Old Testament": [
        "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges",
        "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles",
        "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
        "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
        "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
        "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    ],
    "New Testament": [
        "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
        "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
        "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus",
        "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
        "3 John", "Jude", "Revelation",
    ],
    "KJV Bible": [],
    "Bible": [],
}


def book_index(scripture_set, book):
    lst = BOOK_ORDER.get(scripture_set, [])
    if book in lst:
        return lst.index(book)
    m = re.match(r"^\d+", book or "")
    num = int(m.group(0)) if m else 9999
    return 10000 + num


def sort_chapters(chapters):
    def key(c):
        num_m = re.search(r"\d+", c.get("chapter", "") or "")
        num = int(num_m.group(0)) if num_m else 0
        return (
            c.get("scriptureSet", "") or "",
            book_index(c.get("scriptureSet", ""), c.get("book", "")),
            num,
            c.get("chapter", "") or "",
        )
    return sorted(chapters, key=key)


CHAPTER_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>{book} — {chapter}</title>
<link rel="stylesheet" href="../chapter_player.css">
</head>
<body>
<script>
window.CHAPTER_DATA = {{
  scriptureSet: {scripture_set_json},
  book: {book_json},
  chapter: {chapter_json},
  audioSrc: {audio_src_json},
  lyrics: {lyrics_json}
}};
</script>
<script src="../chapter_player.js"></script>
</body>
</html>"""


def js_str(s):
    return json.dumps(s, ensure_ascii=False)


def file_slug(scripture_set, book, chapter):
    raw = f"{scripture_set}-{book}-{chapter}".lower()
    return re.sub(r"[^a-z0-9]+", "-", raw).strip("-")


def build_chapter_html(scripture_set, book, chapter, audio_url, lyrics):
    lyrics_json = json.dumps(lyrics, ensure_ascii=False, separators=(",", ":"))
    return CHAPTER_HTML_TEMPLATE.format(
        book=book, chapter=chapter,
        scripture_set_json=js_str(scripture_set),
        book_json=js_str(book),
        chapter_json=js_str(chapter),
        audio_src_json=js_str(audio_url),
        lyrics_json=lyrics_json,
    )


def lyrics_from_vtt(vtt_text):
    cues = parse_vtt(vtt_text)
    return [{"time": round(c["startSec"], 3), "text": c["text"]} for c in cues]


FIELD_RE = {
    "scriptureSet": re.compile(r'scriptureSet:\s*("(?:[^"\\]|\\.)*")'),
    "book": re.compile(r'book:\s*("(?:[^"\\]|\\.)*")'),
    "chapter": re.compile(r'chapter:\s*("(?:[^"\\]|\\.)*")'),
    "audioSrc": re.compile(r'audioSrc:\s*("(?:[^"\\]|\\.)*")'),
}
LYRICS_RE = re.compile(r"lyrics:\s*(\[.*\])\s*\n?\};", re.DOTALL)


def _extract_chapter_data(text):
    """Extract CHAPTER_DATA fields directly via targeted regex instead of
    converting the whole JS object literal to JSON (which breaks if any verse
    text happens to contain a colon)."""
    data = {}
    for key, pat in FIELD_RE.items():
        m = pat.search(text)
        if m:
            data[key] = json.loads(m.group(1))
    m = LYRICS_RE.search(text)
    if m:
        data["lyrics"] = json.loads(m.group(1))
    return data


def bootstrap_library_from_chapterfiles(site_dir, source_files_dir):
    entries = []
    chapterfiles_dir = site_dir / "chapterfiles"
    if not chapterfiles_dir.exists():
        return entries

    for html_path in sorted(chapterfiles_dir.glob("*.html")):
        text = html_path.read_text(encoding="utf-8", errors="replace")
        if "CHAPTER_DATA" not in text:
            print(f"  (skipping {html_path.name} -- no CHAPTER_DATA found)", file=sys.stderr)
            continue
        try:
            data = _extract_chapter_data(text)
        except json.JSONDecodeError as e:
            print(f"  (skipping {html_path.name} -- could not parse CHAPTER_DATA: {e})", file=sys.stderr)
            continue
        if not data.get("book") or not data.get("chapter"):
            print(f"  (skipping {html_path.name} -- incomplete CHAPTER_DATA)", file=sys.stderr)
            continue

        duration = 0
        lyrics = data.get("lyrics") or []
        if lyrics:
            duration = round(lyrics[-1].get("time", 0)) + 10

        if source_files_dir and source_files_dir.exists():
            chapter_num_m = re.search(r"\d+", data.get("chapter", "") or "")
            if chapter_num_m:
                chapter_dir = source_files_dir / data.get("book", "") / chapter_num_m.group(0)
                if chapter_dir.exists():
                    for mp3 in chapter_dir.glob("*.mp3"):
                        d = ffprobe_duration(mp3)
                        if d:
                            duration = round(d)
                            break

        entries.append({
            "scriptureSet": data.get("scriptureSet", "General"),
            "book": data.get("book", "Unknown"),
            "chapter": data.get("chapter", "Chapter"),
            "file": f"chapterfiles/{html_path.name}",
            "audioSrc": data.get("audioSrc", ""),
            "duration": duration,
        })

    return entries


def ffprobe_duration(mp3_path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(mp3_path)],
            capture_output=True, text=True, check=True,
        )
        return float(out.stdout.strip())
    except Exception:
        return None


def load_library(site_dir, source_files_dir):
    lib_path = site_dir / "library.json"
    if lib_path.exists():
        return json.loads(lib_path.read_text(encoding="utf-8"))
    print("No library.json found -- bootstrapping from existing chapterfiles/*.html...")
    entries = bootstrap_library_from_chapterfiles(site_dir, source_files_dir)
    print(f"  Bootstrapped {len(entries)} chapter(s) into library.json")
    return entries


def save_library(site_dir, entries):
    lib_path = site_dir / "library.json"
    lib_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")


def fmt_duration(seconds):
    if not seconds:
        return ""
    m = int(seconds // 60)
    s = str(int(seconds % 60)).zfill(2)
    return f"{m}:{s}"


def build_index_html(chapters):
    sets = {}
    for c in chapters:
        ss = c.get("scriptureSet") or "General"
        bk = c.get("book") or "Unknown"
        sets.setdefault(ss, {}).setdefault(bk, []).append(c)

    sidebar_items = []
    for ss, books in sets.items():
        book_html = []
        for bk, chs in books.items():
            chapter_links = "".join(
                f'<a class="chapter-item" href="{c["file"]}">{c["chapter"]}</a>' for c in chs
            )
            book_html.append(
                '<div class="book-section">'
                '<div class="book-label" onclick="this.classList.toggle(\'open\');this.nextElementSibling.classList.toggle(\'open\')">'
                f'— {bk} <span class="arrow">▶</span></div>'
                f'<div class="chapter-list">{chapter_links}</div>'
                '</div>'
            )
        sidebar_items.append(
            '<div class="set-section">'
            '<div class="set-label" onclick="this.classList.toggle(\'open\');this.nextElementSibling.classList.toggle(\'open\')">'
            f'{ss} <span class="arrow">▶</span></div>'
            f'<div class="set-list">{"".join(book_html)}</div>'
            '</div>'
        )
    sidebar_html = "".join(sidebar_items)

    grid_items = []
    for ss, books in sets.items():
        book_groups = []
        for bk, chs in books.items():
            cards = []
            for c in chs:
                dur_str = fmt_duration(c.get("duration"))
                dur_html = f'<span class="card-duration">{dur_str}</span>' if dur_str else ""
                cards.append(
                    f'<a class="chapter-card" href="{c["file"]}">'
                    '<div class="play-icon">▶</div>'
                    '<div class="card-text">'
                    f'<div class="card-chapter">{c["chapter"]}</div>'
                    f'<div class="card-book">{bk}{dur_html}</div>'
                    '</div></a>'
                )
            book_groups.append(
                '<div class="book-group">'
                f'<div class="book-group-title">{bk}</div>'
                f'<div class="chapter-grid">{"".join(cards)}</div>'
                '</div>'
            )
        grid_items.append(
            f'<div class="set-group"><div class="set-group-title">{ss}</div>{"".join(book_groups)}</div>'
        )
    grid_html = "".join(grid_items) if chapters else '<div class="empty-state"><div class="big">\U0001F4D6</div><h3>No chapters yet</h3></div>'

    sidebar_or_empty = sidebar_html or '<p style="padding:16px 20px;font-size:13px;color:var(--muted);font-style:italic;">No chapters yet.</p>'

    head = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0, viewport-fit=cover\">\n"
        "<meta name=\"mobile-web-app-capable\" content=\"yes\">\n"
        "<meta name=\"apple-mobile-web-app-capable\" content=\"yes\">\n"
        "<meta name=\"apple-mobile-web-app-status-bar-style\" content=\"black-translucent\">\n"
        "<title>Scripture Reader</title>\n<style>\n"
        "@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap');\n"
        "*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}\n"
        "body{background:#0e0d0b;color:#ede8df;font-family:'Lora',Georgia,serif;min-height:100vh;}\n"
        ".layout{display:flex;min-height:100vh;}\n"
        ".sidebar{width:260px;flex-shrink:0;background:#161512;border-right:1px solid rgba(255,255,255,0.07);display:flex;flex-direction:column;position:sticky;top:0;height:100vh;overflow-y:auto;}\n"
        ".sidebar-header{padding:22px 20px 16px;border-bottom:1px solid rgba(255,255,255,0.07);}\n"
        ".app-title{font-size:18px;font-weight:600;letter-spacing:-0.01em;line-height:1.2;}\n"
        ".app-sub{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#c8a96e;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;}\n"
        ".book-nav{padding:8px 0;flex:1;}\n"
        ".set-section{margin-bottom:2px;}\n"
        ".set-label{display:flex;align-items:center;justify-content:space-between;padding:9px 20px;font-size:14px;font-weight:600;color:#ede8df;cursor:pointer;user-select:none;background:rgba(255,255,255,0.03);}\n"
        ".set-label:hover{color:#c8a96e;}\n"
        ".set-list{display:none;}\n"
        ".set-list.open{display:block;}\n"
        ".book-section{margin-bottom:0;}\n"
        ".book-label{display:flex;align-items:center;justify-content:space-between;padding:7px 20px 7px 32px;font-size:13px;font-weight:500;color:#6e6a62;cursor:pointer;user-select:none;}\n"
        ".book-label:hover{color:#ede8df;}\n"
        ".chapter-list{display:none;padding:0 0 4px;}\n"
        ".chapter-list.open{display:block;}\n"
        ".chapter-item{display:block;padding:5px 20px 5px 44px;font-size:12px;color:#6e6a62;text-decoration:none;font-family:'IBM Plex Mono',monospace;}\n"
        ".chapter-item:hover{color:#ede8df;background:rgba(255,255,255,0.03);}\n"
        ".arrow{font-size:10px;transition:transform 0.2s;opacity:0.4;font-family:'IBM Plex Mono',monospace;}\n"
        ".set-label.open .arrow,.book-label.open .arrow{transform:rotate(90deg);}\n"
        ".main{flex:1;padding:3rem 2.5rem;max-width:860px;}\n"
        ".welcome{margin-bottom:3rem;}\n"
        ".welcome h2{font-size:28px;font-weight:600;letter-spacing:-0.02em;margin-bottom:8px;}\n"
        ".welcome p{font-size:15px;color:#6e6a62;line-height:1.7;max-width:520px;font-style:italic;}\n"
        ".section-title{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#c8a96e;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:20px;padding-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.07);}\n"
        ".set-group{margin-bottom:3rem;}\n"
        ".set-group-title{font-size:22px;font-weight:600;letter-spacing:-0.02em;margin-bottom:20px;border-bottom:1px solid rgba(255,255,255,0.07);padding-bottom:10px;}\n"
        ".book-group{margin-bottom:2rem;}\n"
        ".book-group-title{font-size:17px;font-weight:500;letter-spacing:-0.01em;margin-bottom:12px;color:#6e6a62;}\n"
        ".chapter-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;}\n"
        ".chapter-card{display:flex;align-items:center;gap:12px;background:#161512;border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:14px 16px;text-decoration:none;color:#ede8df;transition:background 0.15s,border-color 0.15s,transform 0.1s;}\n"
        ".chapter-card:hover{background:#1d1c18;border-color:rgba(255,255,255,0.12);transform:translateY(-1px);}\n"
        ".play-icon{width:32px;height:32px;background:rgba(200,169,110,0.12);border:1px solid rgba(200,169,110,0.25);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;color:#c8a96e;}\n"
        ".card-chapter{font-size:14px;font-weight:500;}\n"
        ".card-book{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#6e6a62;margin-top:2px;text-transform:uppercase;letter-spacing:0.06em;display:flex;align-items:center;gap:6px;}\n"
        ".card-duration{color:#c8a96e;opacity:0.8;}\n"
        ".empty-state{text-align:center;padding:4rem 2rem;color:#6e6a62;}\n"
        ".empty-state .big{font-size:40px;margin-bottom:16px;opacity:0.4;}\n"
        ".empty-state h3{font-size:18px;font-weight:500;margin-bottom:8px;color:#ede8df;}\n"
        "@media(max-width:640px){.sidebar{display:none;}.main{padding:1.5rem 1rem;}.chapter-grid{grid-template-columns:1fr;}}\n"
        "</style>\n</head>\n<body>\n"
    )

    body = (
        '<div class="layout">\n'
        '  <nav class="sidebar">\n'
        '    <div class="sidebar-header"><div class="app-title">Scripture Reader</div>'
        '<div class="app-sub">Audio · Text · Sync</div></div>\n'
        f'    <div class="book-nav">{sidebar_or_empty}</div>\n'
        '  </nav>\n'
        '  <main class="main">\n'
        '    <div class="welcome"><h2>Library</h2><p>Select a scripture set, book, and chapter to begin listening and reading along.</p></div>\n'
        '    <div class="section-title">Scripture Library</div>\n'
        f'    <div>{grid_html}</div>\n'
        '  </main>\n'
        '</div>\n</body>\n</html>'
    )

    return head + body


CSV_HEADERS = ["Timestamp", "Scripture Set", "Book", "Chapter", "MP3 URL",
               "Avg Chars Per Line", "Seconds Used", "Chars Per Unit",
               "Audio File", "Text File"]


def append_export_log(log_path, scripture_set, book, chapter, audio_url, audio_file, text_file):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [now, scripture_set, book, chapter, audio_url, "0", "11", "153", audio_file, text_file]
    is_new = not log_path.exists()
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        if is_new:
            writer.writerow(CSV_HEADERS)
        writer.writerow(row)


def main():
    ap = argparse.ArgumentParser(description="Export a chapter player from a verse-aligned VTT.")
    ap.add_argument("--site", required=True)
    ap.add_argument("--vtt", required=True)
    ap.add_argument("--scripture-set", required=True)
    ap.add_argument("--book", required=True)
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--audio-url", required=True)
    ap.add_argument("--mp3")
    ap.add_argument("--source-files")
    ap.add_argument("--log")
    args = ap.parse_args()

    site_dir = Path(args.site)
    vtt_path = Path(args.vtt)
    chapterfiles_dir = site_dir / "chapterfiles"
    chapterfiles_dir.mkdir(parents=True, exist_ok=True)

    vtt_text = vtt_path.read_text(encoding="utf-8", errors="replace")
    lyrics = lyrics_from_vtt(vtt_text)
    if not lyrics:
        print("ERROR: No cues parsed from VTT.", file=sys.stderr)
        sys.exit(1)

    slug = file_slug(args.scripture_set, args.book, args.chapter)
    chapter_html = build_chapter_html(args.scripture_set, args.book, args.chapter, args.audio_url, lyrics)
    chapter_path = chapterfiles_dir / f"{slug}.html"
    chapter_path.write_text(chapter_html, encoding="utf-8")
    print(f"Wrote:   {chapter_path}")

    duration = 0
    if args.mp3:
        d = ffprobe_duration(Path(args.mp3))
        if d:
            duration = round(d)
    if not duration:
        duration = round(lyrics[-1]["time"]) + 10

    source_files_dir = Path(args.source_files) if args.source_files else None
    library = load_library(site_dir, source_files_dir)
    entry = {
        "scriptureSet": args.scripture_set,
        "book": args.book,
        "chapter": args.chapter,
        "file": f"chapterfiles/{slug}.html",
        "audioSrc": args.audio_url,
        "duration": duration,
    }
    existing_idx = None
    for i, c in enumerate(library):
        if c.get("scriptureSet") == args.scripture_set and c.get("book") == args.book and c.get("chapter") == args.chapter:
            existing_idx = i
            break
    if existing_idx is not None:
        library[existing_idx] = entry
    else:
        library.append(entry)
    library = sort_chapters(library)
    save_library(site_dir, library)
    print(f"Wrote:   {site_dir / 'library.json'}  ({len(library)} chapters)")

    index_html = build_index_html(library)
    (site_dir / "index.html").write_text(index_html, encoding="utf-8")
    print(f"Wrote:   {site_dir / 'index.html'}")

    log_path = Path(args.log) if args.log else site_dir.parent / "scripture_export_log.csv"
    append_export_log(
        log_path, args.scripture_set, args.book, args.chapter, args.audio_url,
        Path(args.mp3).name if args.mp3 else "(none)", vtt_path.name,
    )
    print(f"Logged:  {log_path}")
    print("Done.")


if __name__ == "__main__":
    main()