---
name: scripture-audio-sync-reader
description: >
  Build a fully self-contained, mobile-friendly scripture audio reader with
  synchronized scrolling text from audio + transcript files. Use this skill
  whenever the user wants to: sync audio with scrolling text, build an audio
  book or scripture reader, export chapter HTML players, manage a multi-book
  library with a public index, host a reader on Netlify, time text to audio
  by character count, parse SSML/LRC/VTT/SRT/TXT transcripts, or restore
  deleted chapters from existing HTML files. Also triggers for: "audio sync
  player", "scripture reader", "chapter player", "scrolling text with audio",
  "text follows along with audio", "MP3 with transcript", or any request to
  build a listen-and-read-along experience. The skill covers the full
  pipeline from transcript timing through export, library management, hosting,
  and version control.
---

# Scripture Audio Sync Reader

A complete pipeline for building a listen-and-read-along audio reader:
character-based transcript timing → chapter HTML export → library index
generation → Netlify hosting. Designed for scripture but works for any
audio + text pairing (audiobooks, lectures, podcasts).

---

## System Overview

Five files power the entire system:

| File | Role | Deployed? |
|---|---|---|
| `audio_sync_player.html` | Admin: timing tool + chapter export | No (local only) |
| `scripture_reader.html` | Admin: library manager + index export | No (local only) |
| `chapter_player.js` | Shared: powers all chapter pages | Yes |
| `chapter_player.css` | Shared: styles all chapter pages | Yes |
| `index.html` | Public: reader with baked-in chapter list | Yes |

Folder structure on Netlify:
```
root/
├── index.html
├── chapter_player.js
├── chapter_player.css
└── chapterfiles/
    └── scripture-set-book-chapter.html
```

Audio is hosted externally (Archive.org recommended) and referenced by URL.

---

## Trigger Contexts

Use this skill when the user asks about any of:
- Syncing MP3 audio with scrolling text
- Building an audio book / scripture reader
- Timing text to audio by character count
- Parsing SSML, LRC, VTT, SRT, or TXT transcript files
- Exporting chapter HTML players
- Managing a book/chapter library with a public index page
- Hosting a reader on Netlify
- Restoring deleted chapters from saved HTML files
- Mobile-safe audio player layout (safe area insets, dvh units)
- Versioning a multi-file web project

---

## Workflow

### Step 1 — Prepare audio (Archive.org)

Upload MP3 to `archive.org/upload`. After upload, get the direct URL:
- ✗ Wrong: `archive.org/details/item-name` (item page, won't stream)
- ✓ Correct: `archive.org/download/item-name/file.mp3` (direct stream)

Archive.org is preferred over Google Drive (Drive serves download-intent
URLs that `<audio>` elements can't stream) and Dropbox (requires `?dl=1`
suffix workaround).

### Step 2 — Set timing in audio_sync_player.html

1. Drop MP3 + transcript onto the drop zone
2. Adjust timing rate (default: 153 chars = 11 seconds per line)
3. Click Recalculate — blue info bar shows calc duration vs audio length
4. Play back and verify text scrolls in sync
5. Use "✕ Clear files" between chapters to reset state

### Step 3 — Export chapter

Fill in Export panel:
- **Scripture Set** — top-level grouping (e.g. Book of Mormon, KJV Bible)
- **Book** — second-level (e.g. 1 Nephi)
- **Chapter** — third-level (e.g. Chapter 1)
- **MP3 URL** — Archive.org /download/ URL

Click **Export Chapter Player** → two files download automatically:
- `scripture-set-book-chapter.html` → place in `chapterfiles/`
- `index.html` → replace root `index.html`

Export also:
- Appends a record to the export log (localStorage)
- Writes chapter entry to localStorage (shared with admin reader)

### Step 4 — Manage library (scripture_reader.html)

- **Add chapter**: paste exported JSON or fill in manual fields
- **Restore from HTML**: pick a previously exported chapter HTML file —
  reads `CHAPTER_DATA` using `Function` constructor sandbox, no re-timing needed
- **Selective delete**: ✕ per chapter, Remove book, Remove set (all with confirm)
- **Export index.html**: regenerates public reader from current library

### Step 5 — Deploy to Netlify

1. Zip the root folder (index.html + chapter_player.js/css + chapterfiles/)
2. Drop zip at `netlify.com/drop`
3. Get public URL — works on any device, no login required

Updating: re-export chapter → two files download → replace old files → re-zip → drop

---

## Transcript Format Support

| Format | Timestamps | Notes |
|---|---|---|
| `.lrc` | Yes | `[MM:SS.ss]Text` — most precise |
| `.vtt` | Yes | WebVTT — from video tools / transcription services |
| `.srt` | Yes | Standard subtitle format |
| `.ssml` | No | Tags stripped via DOMParser; `<p>`, `<s>`, `<break>` → segments |
| `.txt` | No | One line per segment; evenly spaced by char count |

For formats without timestamps, timing is calculated as:
`duration = (charCount / CHARS_PER_UNIT) × SECS_PER_UNIT`

Default rate: 153 chars = 11 seconds (derived from avg chars/line of
the user's specific text file — measure with `wc` or a char counter).

---

## Character-Based Timing

The timing engine spaces lines proportionally by character count:
- Each line's duration = `(line.length / CHARS_PER_UNIT) × SECS_PER_UNIT`
- Short lines get less time, long lines get more
- The blue info bar shows: lines · chars · avg c/line · calc duration · ±diff vs audio

**Tuning workflow:**
1. Load both MP3 and transcript
2. Note the ±diff vs audio in the info bar
3. Adjust CHARS_PER_UNIT or SECS_PER_UNIT
4. Recalculate — diff updates immediately
5. Play back to verify

---

## Library Hierarchy & Sort Order

Three levels: **Scripture Set → Book → Chapter**

Books sort by canonical scripture order (not alphabetical):

| Scripture Set | Order |
|---|---|
| Book of Mormon | 1 Nephi → 2 Nephi → Jacob → Enos → Jarom → Omni → Words of Mormon → Mosiah → Alma → Helaman → 3 Nephi → 4 Nephi → Mormon → Ether → Moroni |
| Old Testament | Genesis → … → Malachi (39 books) |
| New Testament | Matthew → … → Revelation (27 books) |
| Pearl of Great Price | Moses → Abraham → JS-Matthew → JS-History → Articles of Faith |
| Doctrine and Covenants | Numeric by section number |
| Unknown sets | Leading number extracted, then alphabetical |

Chapters sort numerically (Chapter 2 before Chapter 10).
Sort runs automatically on every save and on page load.

---

## Mobile Layout (chapter_player.css)

Key techniques for mobile browser compatibility:

```css
/* Dynamic viewport height — excludes browser chrome and nav bars */
height: 100dvh;  /* falls back to 100vh on older browsers */

/* Safe area insets — clears notch, status bar, home indicator */
--safe-top:    env(safe-area-inset-top,    0px);
--safe-bottom: env(safe-area-inset-bottom, 0px);

/* Apply to header and footer */
.cp-header    { padding-top:    calc(14px + var(--safe-top)); }
.cp-controls  { padding-bottom: calc(16px + var(--safe-bottom)); }
```

Required meta tags on every generated page:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
```

`chapter_player.js` also patches `viewport-fit=cover` at runtime so
existing (pre-v4) chapter HTML files get the fix without re-exporting.

---

## Export Log

Every export appends a structured record to localStorage (`scripture_export_log_v2`).
Stored as a JSON array. Fields:

| Field | Description |
|---|---|
| timestamp | ISO datetime (local) |
| scriptureSet | Scripture set name |
| book | Book name |
| chapter | Chapter name |
| audioSrc | Archive.org MP3 URL |
| avgCharsLine | Average chars per line at export time |
| secondsUsed | SECS_PER_UNIT value used |
| charsPerUnit | CHARS_PER_UNIT value used |
| audioFile | Local MP3 filename (or "(none)") |
| textFile | Local transcript filename (or "(pasted)") |

Download as CSV via **Download export log** button → `scripture_export_log.csv`.
Each download is the full log (Option A — complete file, not append-only),
since the browser cannot write to an existing local file.

Old pipe-delimited format (pre-v2) is auto-migrated to JSON on first open.

---

## Restore from Chapter HTML

When a chapter is accidentally deleted from the library but the HTML file
still exists:

1. Open `scripture_reader.html` → Add chapter panel
2. Click "Choose chapter HTML file" → select the `.html` from `chapterfiles/`
3. The file is parsed using `new Function('window', scriptBody)` — a sandbox
   that executes only the `window.CHAPTER_DATA = {...}` assignment
4. Extracted fields: scriptureSet, book, chapter, audioSrc, filename
5. Chapter re-registered in library; sort applied automatically

**Why `Function` constructor instead of regex/JSON.parse:**
The `lyrics` array contains hundreds of objects with arbitrary text
(apostrophes, quotes, special chars) that break regex extraction and
JSON.parse. The `Function` sandbox lets the JS engine parse it natively.

**Why not an iframe:**
Iframe blob URL approach caused the injected script to leak as visible
text into the parent page's DOM. `Function` constructor is cleaner and
has no DOM side effects.

---

## localStorage Keys

| Key | Contents |
|---|---|
| `scripture_reader_chapters_v2` | JSON array of chapter entries |
| `scripture_export_log_v2` | JSON array of export log records |

Migration: `textfiles/` → `chapterfiles/` prefix runs automatically on
`loadChapters()` / `loadLibrary()` and saves back so it only runs once.

---

## Edge Cases Handled

### Audio
- **Google Drive URLs** — `/uc?export=download` serves download-intent,
  not streamable. Replaced with Archive.org.
- **`/details/` vs `/download/`** — Archive.org item page vs direct file.
  Player shows error with the attempted URL if audio fails.
- **crossOrigin required** — `audio.crossOrigin = 'anonymous'` needed for
  Archive.org streaming from a different domain.
- **Silent play() failures** — `audio.play()` returns a Promise; errors
  caught and displayed on screen rather than silently swallowed.

### Transcript parsing
- **SSML with large lyrics arrays** — regex/JSON extraction breaks on
  apostrophes, quotes, special chars. Use `Function` constructor sandbox.
- **SSML loaded before audio** — duration is 0, so spacing defaults to
  4s/line. Fixed by storing rawSegments and re-spacing on `loadedmetadata`.
- **Old localStorage format** — pipe-delimited log strings auto-migrated
  to JSON array on first open.

### DOM
- **`innerHTML = ''` destroying child nodes** — `#no-lyrics` div was
  being destroyed then re-appended as a detached node, silently aborting
  `renderLyrics`. Fixed by writing empty-state as innerHTML string directly.
- **Inline `onclick` with `JSON.stringify`** — double-quoted values break
  HTML attribute parsing. Fixed with `data-action` / `data-ss` / `data-bk`
  / `data-ch` attributes and event delegation on the container.
- **`window.` scope for dynamic buttons** — functions called by inline
  `onclick` must be on `window`. Replaced with event delegation so
  regular function scope works.

### Mobile layout
- **Controls hidden by phone nav bar** — `100vh` includes the nav bar
  area on mobile. Fixed with `100dvh` + `env(safe-area-inset-bottom)`.
- **iOS momentum scrolling** — requires `-webkit-overflow-scrolling: touch`.
- **Tap targets** — minimum 40×40px on all interactive elements.

### Versioning
- **`textfiles/` → `chapterfiles/` migration** — handled in `loadChapters`
  / `loadLibrary` with save-back so migration runs exactly once.
- **localStorage key versioned** — `_v1` → `_v2` so old data doesn't
  conflict with new schema.

### Hosting
- **Netlify iframe embedding** — works from Netlify; audio in cross-origin
  iframes may be blocked by some browsers (autoplay policy).
- **chapterfiles/ path in index.html** — baked in at export time; stale
  paths from pre-`chapterfiles/` exports fixed by re-exporting or by
  migration code in admin tools.

---

## Input / Output Summary

| Input | Format | Used by |
|---|---|---|
| Audio file | .mp3 | audio_sync_player (local timing only) |
| Transcript | .txt .ssml .lrc .vtt .srt | audio_sync_player |
| Archive.org URL | https://archive.org/download/… | export panel |
| Chapter HTML file | .html (previously exported) | restore feature |
| Chapter JSON | {"scriptureSet":…} | scripture_reader add panel |

| Output | Format | Destination |
|---|---|---|
| Chapter player | .html | chapterfiles/ → Netlify |
| Public index | index.html | root → Netlify |
| Chapter JSON | .json or clipboard | scripture_reader add panel |
| Export log | .csv | local only, do not deploy |

---

## Version History Reference

| Version | Key changes |
|---|---|
| v1 | Initial release: timing tool, chapter export, 2-level hierarchy (Book → Chapter), textfiles/ folder |
| v2 | 3-level hierarchy (Set → Book → Chapter), chapterfiles/, export log CSV, selective delete, clear files, Save JSON |
| v3 | Restore from chapter HTML, canonical book sort order |
| v4 | Mobile safe area (dvh, env()), larger tap targets, landscape support |

Rollback files: `*.v1.bak` through `*.v4.bak` kept locally alongside working files.
