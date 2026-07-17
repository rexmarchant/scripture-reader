#!/usr/bin/env python3
"""
vtt_align.py -- Phase 2b automation

Replaces vtt_converter.html. Faithful Python port of its alignment engine
(three-pass: word-stream matching, proportional interpolation, dedup).

Given a V2 SSML file (verse numbers retained) and a Whisper-generated VTT
for the same chapter's audio, produces a verse-aligned VTT where every
verse (and the chapter title) has an exact, non-overlapping timestamp.

Usage:
    python3 vtt_align.py chapter-v2.ssml chapter-whisper.vtt [output.vtt]
    python3 vtt_align.py chapter-v2.ssml --mp3 chapter.mp3 [--model small] [output.vtt]

If no output path is given, derives one the same way the original tool
did: "-whisper" -> "-final-vtt", otherwise append "-final-vtt".
"""

import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


# -- SSML PARSING ------------------------------------------------------------

def parse_ssml_verses(raw: str):
    """Return (title, [(num, text), ...]) from a V2 SSML file."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        # Fallback: strip tags, treat as plain lines
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()
        segments = [s.strip() for s in text.split("\n") if s.strip()]
        return _split_title_and_verses(segments)

    speak = root

    segments = []
    for p in speak.iter():
        tag = p.tag.split("}")[-1].lower()
        if tag in ("p", "sentence", "s"):
            t = "".join(p.itertext())
            t = re.sub(r"\s+", " ", t).strip()
            if t:
                segments.append(t)

    return _split_title_and_verses(segments)


def _split_title_and_verses(segments):
    title = None
    verses = []
    verse_pat = re.compile(r"^(\d+)\.\s*(.*)$", re.DOTALL)
    for text in segments:
        m = verse_pat.match(text)
        if m:
            verses.append((int(m.group(1)), re.sub(r"\s+", " ", text).strip()))
        elif not verses and text.strip():
            title = re.sub(r"\s+", " ", text).strip()
    return title, verses


# -- VTT PARSING --------------------------------------------------------------

TS_RE = re.compile(r"^(\d{1,2}(?::\d{2})?:\d{2}\.\d+)\s+-->\s+(\d{1,2}(?::\d{2})?:\d{2}\.\d+)")


def parse_timestamp(ts: str) -> float:
    parts = ts.split(":")
    if len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])


def sec_to_vtt(sec: float) -> str:
    sec = max(sec, 0)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    s_str = f"{s:06.3f}"
    if h > 0:
        return f"{h:02d}:{m:02d}:{s_str}"
    return f"{m:02d}:{s_str}"


def parse_vtt(raw: str):
    cues = []
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = TS_RE.match(line)
        if m:
            start_str = m.group(1)
            start_sec = parse_timestamp(start_str)
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip() != "":
                text_lines.append(lines[i].strip())
                i += 1
            text = " ".join(text_lines).strip()
            if text:
                cues.append({"start": start_str, "startSec": start_sec, "text": text})
        else:
            i += 1
    return cues


# -- NORMALIZER -----------------------------------------------------------------

def norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def verse_anchor_words(verse_text: str, n: int = 8):
    stripped = re.sub(r"^\d+\.\s*", "", verse_text)
    return [w for w in norm(stripped).split(" ") if w][:n]


def words_match(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) >= 4 and b.startswith(a):
        return True
    if len(b) >= 4 and a.startswith(b):
        return True
    return False


# -- ALIGNMENT ENGINE (3-pass) --------------------------------------------------

def _score_anchor_at(word_list, wi, anchor):
    """Score how well `anchor` matches the word stream starting at index wi."""
    score = 0
    w_offset = 0
    for ai in range(len(anchor)):
        w1 = word_list[wi + w_offset] if wi + w_offset < len(word_list) else None
        w2 = word_list[wi + w_offset + 1] if wi + w_offset + 1 < len(word_list) else None
        if w1 is None:
            break
        if words_match(w1["word"], anchor[ai]):
            score += 1
            w_offset += 1
        elif w2 is not None and words_match(w2["word"], anchor[ai]):
            w_offset += 2
        else:
            break
    return score


def _search_anchor_window(word_list, start, limit, anchor):
    """Scan word_list[start:limit) for the best anchor match.
    Returns (best_word_idx, best_score)."""
    best_word_idx = -1
    best_score = 0
    limit = min(limit, len(word_list))
    wi = max(start, 0)
    while wi < limit:
        if not words_match(word_list[wi]["word"], anchor[0] if anchor else ""):
            wi += 1
            continue
        score = _score_anchor_at(word_list, wi, anchor)
        if score > best_score:
            best_score = score
            best_word_idx = wi
        if best_score >= min(6, len(anchor)):
            break
        wi += 1
    return best_word_idx, best_score


def align_verses(verses, cues):
    word_list = []  # each: {word, cueIdx, startSec}
    for ci, cue in enumerate(cues):
        cue_words = [w for w in norm(cue["text"]).split(" ") if w]
        cue_end = cues[ci + 1]["startSec"] if ci + 1 < len(cues) else cue["startSec"] + 5
        cue_dur = cue_end - cue["startSec"]
        n = len(cue_words)
        for wi, w in enumerate(cue_words):
            word_sec = cue["startSec"] + (wi / n) * cue_dur if n else cue["startSec"]
            word_list.append({"word": w, "cueIdx": ci, "startSec": word_sec})

    total_duration = cues[-1]["startSec"] + 5

    # Proportional-position lookup (by character offset) used as a recovery
    # anchor below -- lets a stuck search pointer "un-stick" itself instead
    # of cascading failures through the rest of a long chapter.
    total_chars = sum(len(t) for _, t in verses) or 1
    cum_chars = []
    running = 0
    for _, t in verses:
        cum_chars.append(running)
        running += len(t)

    # PASS 1: word-stream matching
    raw = []
    word_search_start = 0
    SEARCH_WINDOW = 1500  # words -- generous forward window per verse

    for verse_idx, (verse_num, verse_text) in enumerate(verses):
        anchor = verse_anchor_words(verse_text, 8)

        search_limit = word_search_start + SEARCH_WINDOW
        best_word_idx, best_score = _search_anchor_window(
            word_list, word_search_start, search_limit, anchor
        )

        weak_match = best_word_idx == -1 or best_score < min(4, len(anchor))
        if weak_match:
            # Recovery: estimate where this verse should fall based on its
            # proportional position (by character count) through the whole
            # chapter, and search a window around that estimate. Unlike the
            # forward-only search above, this can land anywhere in the
            # transcript, so it can recover a search pointer that got
            # stranded by an earlier ambiguous/short verse.
            est_idx = int((cum_chars[verse_idx] / total_chars) * len(word_list))
            rec_idx, rec_score = _search_anchor_window(
                word_list, est_idx - 500, est_idx + 500, anchor
            )
            if rec_score > best_score:
                best_word_idx, best_score = rec_idx, rec_score

        if best_score >= min(8, len(anchor)):
            confidence = "high"
        elif best_score >= min(5, len(anchor)):
            confidence = "mid"
        else:
            confidence = "low"

        if best_word_idx != -1:
            candidate_sec = word_list[best_word_idx]["startSec"]

            avg_secs_per_verse = total_duration / len(verses)
            matched_secs = [r["startSec"] for r in raw if not r["interpolated"]]
            last_matched_sec = max(matched_secs) if matched_secs else 0
            plausible_max = last_matched_sec + avg_secs_per_verse * 3

            if candidate_sec > plausible_max and confidence != "high":
                raw.append({
                    "num": verse_num, "text": verse_text, "startSec": -1,
                    "timestamp": "", "confidence": "low", "score": best_score,
                    "maxScore": len(anchor), "wordIdx": -1, "interpolated": True,
                })
            else:
                raw.append({
                    "num": verse_num, "text": verse_text, "startSec": candidate_sec,
                    "timestamp": sec_to_vtt(candidate_sec), "confidence": confidence,
                    "score": best_score, "maxScore": len(anchor),
                    "wordIdx": best_word_idx, "interpolated": False,
                })
                word_search_start = best_word_idx + 1
        else:
            raw.append({
                "num": verse_num, "text": verse_text, "startSec": -1,
                "timestamp": "", "confidence": "low", "score": 0,
                "maxScore": len(anchor), "wordIdx": -1, "interpolated": True,
            })

    # PASS 2: interpolate missing timestamps
    vi = 0
    while vi < len(raw):
        if not raw[vi]["interpolated"]:
            vi += 1
            continue

        prev_anchored = -1
        for i in range(vi - 1, -1, -1):
            if not raw[i]["interpolated"]:
                prev_anchored = i
                break
        next_anchored = -1
        for i in range(vi + 1, len(raw)):
            if not raw[i]["interpolated"]:
                next_anchored = i
                break

        t_start = raw[prev_anchored]["startSec"] if prev_anchored >= 0 else 0
        t_end = raw[next_anchored]["startSec"] if next_anchored >= 0 else total_duration

        run_start = prev_anchored + 1
        run_end = next_anchored if next_anchored >= 0 else len(raw)
        run_verses = raw[run_start:run_end]

        run_chars = sum(len(v["text"]) for v in run_verses)
        run_duration = t_end - t_start
        n_run = len(run_verses)

        elapsed = 0
        for ri, v in enumerate(run_verses):
            if run_chars > 0:
                frac = (elapsed + len(v["text"]) * 0.5) / run_chars
            else:
                frac = (ri + 1) / (n_run + 1)
            frac = max(frac, (ri + 1) / (n_run + 1) * 0.3)
            sec = t_start + frac * run_duration
            v["startSec"] = min(sec, t_end - 0.1)
            v["timestamp"] = sec_to_vtt(v["startSec"])
            v["confidence"] = "mid"
            elapsed += len(v["text"])

        vi = run_end

    # PASS 3: deduplicate, minimum 0.1s gap
    MIN_GAP = 0.1
    for i in range(1, len(raw)):
        min_start = raw[i - 1]["startSec"] + MIN_GAP
        if raw[i]["startSec"] < min_start:
            raw[i]["startSec"] = min_start
            raw[i]["timestamp"] = sec_to_vtt(min_start)

    return raw


def build_output_vtt(aligned, title):
    out = "WEBVTT\n\n"

    if title and aligned:
        verse1_start = max(aligned[0]["startSec"], 0.1)
        out += f"{sec_to_vtt(0)} --> {sec_to_vtt(verse1_start)}\n"
        out += f"{title}\n\n"
        if aligned[0]["startSec"] < 0.1:
            aligned[0]["startSec"] = 0.1
            aligned[0]["timestamp"] = sec_to_vtt(0.1)

    for i, cur in enumerate(aligned):
        nxt = aligned[i + 1] if i + 1 < len(aligned) else None
        end_sec = nxt["startSec"] if nxt else cur["startSec"] + 10
        out += f"{sec_to_vtt(cur['startSec'])} --> {sec_to_vtt(end_sec)}\n"
        out += f"{cur['text']}\n\n"

    return out


def derive_output_name(vtt_path: Path) -> Path:
    base = vtt_path.stem
    if re.search(r"-whisper$", base, re.IGNORECASE):
        base = re.sub(r"-whisper$", "-final-vtt", base, flags=re.IGNORECASE)
    else:
        base = base + "-final-vtt"
    return vtt_path.with_name(base + ".vtt")


def run_whisper(mp3_path: Path, model: str = "small") -> Path:
    """Run the Whisper CLI on an mp3 and return the path to the raw .vtt it produces."""
    import subprocess

    out_dir = mp3_path.parent
    cmd = [sys.executable, "-m", "whisper", str(mp3_path),
           "--model", model, "--output_format", "vtt", "--output_dir", str(out_dir)]
    print(f"Running Whisper ({model} model) on {mp3_path.name} -- this can take a while...")
    subprocess.run(cmd, check=True)
    produced = out_dir / (mp3_path.stem + ".vtt")
    if not produced.exists():
        raise FileNotFoundError(f"Expected Whisper output not found: {produced}")
    return produced


def main():
    if len(sys.argv) < 3:
        print(
            "Usage:\n"
            "  python3 vtt_align.py <v2.ssml> <whisper.vtt> [output.vtt]\n"
            "  python3 vtt_align.py <v2.ssml> --mp3 <chapter.mp3> [--model small] [output.vtt]",
            file=sys.stderr,
        )
        sys.exit(1)

    ssml_path = Path(sys.argv[1])

    if sys.argv[2] == "--mp3":
        mp3_path = Path(sys.argv[3])
        model = "small"
        rest = sys.argv[4:]
        if rest and rest[0] == "--model":
            model = rest[1]
            rest = rest[2:]
        vtt_path = run_whisper(mp3_path, model)
        out_path = Path(rest[0]) if rest else derive_output_name(vtt_path)
    else:
        vtt_path = Path(sys.argv[2])
        out_path = Path(sys.argv[3]) if len(sys.argv) > 3 else derive_output_name(vtt_path)

    ssml_raw = ssml_path.read_text(encoding="utf-8", errors="replace")
    vtt_raw = vtt_path.read_text(encoding="utf-8", errors="replace")

    title, verses = parse_ssml_verses(ssml_raw)
    if not verses:
        print("ERROR: No verse lines found in SSML (use the V2 file).", file=sys.stderr)
        sys.exit(1)

    cues = parse_vtt(vtt_raw)
    if not cues:
        print("ERROR: No cues found in Whisper VTT.", file=sys.stderr)
        sys.exit(1)

    aligned = align_verses(verses, cues)
    output_vtt = build_output_vtt(aligned, title)
    out_path.write_text(output_vtt, encoding="utf-8")

    high = sum(1 for a in aligned if not a["interpolated"] and a["confidence"] == "high")
    interpolated = sum(1 for a in aligned if a["interpolated"])
    low = sum(1 for a in aligned if not a["interpolated"] and a["confidence"] == "low")

    print(f"Verses aligned: {len(aligned)}")
    print(f"Word-matched:   {high}")
    print(f"Interpolated:   {interpolated}")
    print(f"Low confidence: {low}")
    print(f"Wrote:          {out_path}")
    if low > 0:
        print("WARNING: some verses had low-confidence matches -- check playback near those verses.", file=sys.stderr)


if __name__ == "__main__":
    main()
