---
name: ssml-converter
description: >
  Converts a scripture .txt file into V1 and V2 SSML files for the Scripture
  Reader project. Use this skill whenever the user says "run the SSML
  converter", "convert scripture to SSML", "convert my txt file", "generate
  SSML", or uploads a .txt file and wants SSML output. ALWAYS use this skill
  for those requests. The user will either upload a .txt file or paste the
  scripture text directly.
---

# SSML Converter Skill

Reads a scripture chapter (uploaded .txt file or pasted text) and outputs
two SSML files as downloads.

## Output files

| File | Purpose |
|---|---|
| `{name}-v1.ssml` | Verse numbers stripped — paste into Amazon Polly (Neural, Patrick voice) |
| `{name}-v2.ssml` | Verse numbers retained — used by vtt_converter.html |

## What to do when triggered

1. If the user uploaded a .txt file, read it with the file reading tools.
   If they pasted text, use that directly.

2. Generate both SSML documents in a single Claude response using the
   system prompt below.

3. Save each as a downloadable file and call present_files.

## SSML generation prompt

Use this exact system instruction when generating the SSML:

---
You are converting scripture text to SSML for Amazon Polly (Neural engine,
Patrick voice) and a synchronized audio reader.

Produce EXACTLY two SSML documents.

DOCUMENT 1 — V1 SSML (for Amazon Polly TTS):
- Valid SSML: <?xml version="1.0" encoding="UTF-8"?><speak>...</speak>
- Remove ALL verse numbers — do not speak them
- Preserve the chapter title as the first <p> (e.g. <p>First Nephi, Chapter 3</p>)
- Each verse = one <p> element with <break time="300ms"/> at the end
- Preserve all scripture text exactly — no paraphrasing, no omissions

DOCUMENT 2 — V2 SSML (for audio sync player):
- Valid SSML: <?xml version="1.0" encoding="UTF-8"?><speak>...</speak>
- KEEP verse numbers at the start of each verse (e.g. 1. And now I, Nephi...)
- Preserve the chapter title as the first <p>
- Each verse = one <p> element
- Preserve all scripture text exactly
---

## File naming

Derive the base name from the uploaded filename or ask the user.
Output files: `{base}-v1.ssml` and `{base}-v2.ssml`

Example: input `1-nep-3-original-text.txt` → `1-nep-3-original-text-v1.ssml`
and `1-nep-3-original-text-v2.ssml`

## After generating

Call present_files with both .ssml files so the user can download them.
Tell the user:
- V1 goes into Amazon Polly
- V2 goes into vtt_converter.html alongside the Whisper VTT

## Notes

- The conversion runs entirely within the Claude conversation — no external
  API calls, no local tool needed.
- Scripture text must be preserved verbatim. Never paraphrase or summarize.
- If the chapter is very long (256+ verses), the output will be large —
  that is expected and correct.
