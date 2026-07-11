# Follow Along Scripture Reader

A synchronized audio scripture reader — plays audio while highlighting the corresponding verse text. Currently covers the Book of Mormon (RLDS/Restored Covenant Edition text), audio generated with Amazon Polly, timing aligned with OpenAI Whisper, audio hosted on Archive.org, site hosted on Netlify.

Live site: https://bom-reader.netlify.app

## Repo layout

- `site/` — the deployed public reader. This is the Netlify **publish directory**.
  - `index.html` — library/index page
  - `chapter_player.js`, `chapter_player.css` — shared chapter player
  - `chapterfiles/` — one HTML file per chapter
- `admin/` — local-only admin tools (never deployed): `admin.html`, `audio_sync_player.html`, `vtt_converter.html`, `scripture_reader.html`
- `docs/` — workflow documentation, SKILL files, version log

See `docs/README.txt` and `docs/Scripture_Reader_workflow_document.txt` for the full chapter-production pipeline (SSML → Polly → Whisper → Archive.org → export → publish).

## Netlify setup

When connecting this repo to Netlify:

- Base directory: (repo root)
- Publish directory: `site`
- Build command: (none — static files)

This keeps `admin/` and `docs/` out of the public deploy while still versioned in git.
