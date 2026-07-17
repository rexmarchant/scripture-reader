#!/usr/bin/env python3
"""
pipeline.py -- full chapter pipeline orchestrator

Runs Phases 1.5 through 6 for a single chapter, end to end:

  1.5  ssml_generate.py       .txt            -> V1 + V2 SSML
  2a   polly_synthesize.py    V1 SSML         -> mp3   (skipped if mp3 already exists, or AWS creds missing)
  2b   vtt_align.py           V2 SSML + mp3   -> verse-aligned VTT (runs Whisper internally)
  3    archive_upload.py      mp3             -> Archive.org /download/ URL (skipped if IA creds missing or --audio-url given)
  4    chapter_export.py      aligned VTT     -> chapterfiles/*.html, library.json, index.html, export log
  5    git add / commit / push in the repo (skipped with --no-git)

Each phase is skipped automatically when its output already exists, so you
can re-run the same command to pick up from wherever you left off (e.g. if
Polly/Archive.org credentials aren't set up yet, do those two steps by hand
and just re-run this to pick up from Whisper alignment onward).

Usage (minimal, credentials already configured):
    python3 pipeline.py \
        --repo "/path/to/Scripture Reader-WORKING" \
        --source-files "/path/to/Source Files" \
        --scripture-set "Book of Mormon" --book "2 Nephi" --chapter-num 16 \
        --txt "/path/to/Source Files/2 Nephi/16/2 Nep Ch 16 orig text.txt"

Usage (no AWS/Archive.org creds yet -- mp3 already recorded/uploaded by hand):
    python3 pipeline.py ... --mp3 "/path/.../2 Nephi Ch 16.mp3" \
        --audio-url "https://archive.org/download/2-nephi-ch-16/2%20Nephi%20Ch%2016.mp3"
"""

import argparse
import functools
import os
import shutil
import subprocess
import sys
from pathlib import Path

print = functools.partial(print, flush=True)  # keep output in order alongside subprocess output

AUTOMATION_DIR = Path(__file__).resolve().parent


def run(cmd, **kwargs):
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"ERROR: command failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)
    return result


def has_aws_creds():
    return bool(os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"))


def has_ia_creds():
    return bool(os.environ.get("IA_ACCESS_KEY") and os.environ.get("IA_SECRET_KEY"))


def git_env():
    """
    Build an environment for git commands that authenticates over SSH using
    the repo-local deploy key (automation/deploy_key), so no personal access
    token ever needs to live in .git/config or be re-entered.

    Works unmodified on Rex's own machine (plain ssh, direct internet).
    Inside a Cowork sandbox session (detected via SANDBOX_RUNTIME, set by
    the sandbox itself), SSH traffic is tunneled through the sandbox's local
    HTTP proxy via socat, since raw outbound port 22 isn't reachable there.
    """
    env = os.environ.copy()
    key_path = AUTOMATION_DIR / "deploy_key"
    if not key_path.exists():
        return env  # no deploy key present -- fall back to whatever git already has configured

    ssh_cmd = f'ssh -i "{key_path}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new'
    if os.environ.get("SANDBOX_RUNTIME") and shutil.which("socat"):
        ssh_cmd += " -o ProxyCommand='socat - PROXY:localhost:%h:%p,proxyport=3128'"
    env["GIT_SSH_COMMAND"] = ssh_cmd
    return env


def main():
    ap = argparse.ArgumentParser(description="Run the full Scripture Reader chapter pipeline.")
    ap.add_argument("--repo", required=True, help='Path to "Scripture Reader-WORKING" (contains site/, automation/, .git)')
    ap.add_argument("--source-files", required=True, help="Path to the Source Files/ folder")
    ap.add_argument("--scripture-set", default="Book of Mormon")
    ap.add_argument("--book", required=True, help='e.g. "2 Nephi"')
    ap.add_argument("--chapter-num", required=True, help='e.g. "16"')
    ap.add_argument("--txt", required=True, help="Path to the source chapter .txt file")
    ap.add_argument("--mp3", help="Existing mp3 path (skips Polly synthesis if given and file exists)")
    ap.add_argument("--audio-url", help="Existing Archive.org /download/ URL (skips upload step if given)")
    ap.add_argument("--whisper-model", default="small")
    ap.add_argument("--no-git", action="store_true", help="Don't commit/push at the end")
    args = ap.parse_args()

    repo = Path(args.repo)
    source_files = Path(args.source_files)
    site_dir = repo / "site"
    chapter_str = f"Chapter {args.chapter_num}"
    txt_path = Path(args.txt)
    chapter_dir = txt_path.parent

    print(f"=== {args.scripture_set} / {args.book} / {chapter_str} ===")

    # -- Phase 1.5: SSML generation --
    base = txt_path.stem.replace(" ", "_")
    v1_path = chapter_dir / f"{base}-v1.ssml"
    v2_path = chapter_dir / f"{base}-v2.ssml"
    if v1_path.exists() and v2_path.exists():
        print(f"[1.5] SSML already exists, skipping: {v1_path.name}, {v2_path.name}")
    else:
        run([sys.executable, str(AUTOMATION_DIR / "ssml_generate.py"), str(txt_path)])

    # -- Phase 2a: Polly synthesis --
    mp3_path = Path(args.mp3) if args.mp3 else chapter_dir / f"{args.book} Ch {args.chapter_num}.mp3"
    if mp3_path.exists():
        print(f"[2a] mp3 already exists, skipping Polly: {mp3_path}")
    elif has_aws_creds():
        run([sys.executable, str(AUTOMATION_DIR / "polly_synthesize.py"), str(v1_path), str(mp3_path)])
    else:
        print(
            f"[2a] SKIPPED -- no AWS credentials in the environment and no mp3 found at {mp3_path}.\n"
            "     Generate the mp3 by hand (or set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY) and re-run.",
            file=sys.stderr,
        )
        sys.exit(1)

    # -- Phase 2b: Whisper + verse alignment --
    aligned_vtt = chapter_dir / f"{base}-final-vtt.vtt"
    if aligned_vtt.exists():
        print(f"[2b] Aligned VTT already exists, skipping: {aligned_vtt.name}")
    else:
        run([
            sys.executable, str(AUTOMATION_DIR / "vtt_align.py"),
            str(v2_path), "--mp3", str(mp3_path), "--model", args.whisper_model,
            str(aligned_vtt),
        ])

    # -- Phase 3: Archive.org upload --
    audio_url = args.audio_url
    if not audio_url:
        if has_ia_creds():
            result = run(
                [
                    sys.executable, str(AUTOMATION_DIR / "archive_upload.py"), str(mp3_path),
                    "--book", args.book, "--chapter-num", args.chapter_num,
                    "--scripture-set", args.scripture_set,
                ],
                capture_output=True, text=True,
            )
            print(result.stdout)
            for line in result.stdout.splitlines():
                if line.startswith("Download URL:"):
                    audio_url = line.split(":", 1)[1].strip()
            if not audio_url:
                print("ERROR: could not parse download URL from archive_upload.py output.", file=sys.stderr)
                sys.exit(1)
        else:
            print(
                "[3] SKIPPED -- no Archive.org credentials in the environment and no --audio-url given.\n"
                "    Upload the mp3 by hand and re-run with --audio-url, or set IA_ACCESS_KEY/IA_SECRET_KEY.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print(f"[3] Using provided --audio-url: {audio_url}")

    # -- Phase 4: chapter export --
    run([
        sys.executable, str(AUTOMATION_DIR / "chapter_export.py"),
        "--site", str(site_dir),
        "--vtt", str(aligned_vtt),
        "--scripture-set", args.scripture_set,
        "--book", args.book,
        "--chapter", chapter_str,
        "--audio-url", audio_url,
        "--mp3", str(mp3_path),
        "--source-files", str(source_files),
        "--log", str(repo / "scripture_export_log.csv"),
    ])

    # -- Phase 5: git commit/push --
    if not args.no_git:
        genv = git_env()
        run(["git", "add", "-A"], cwd=str(repo), env=genv)
        commit_msg = f"Add {args.book} {chapter_str}"
        result = subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(repo), env=genv)
        if result.returncode != 0:
            print("(nothing to commit, or commit failed -- check status above)")
        else:
            run(["git", "push"], cwd=str(repo), env=genv)
    else:
        print("[5] SKIPPED git commit/push (--no-git)")

    print(f"\nDone: {args.book} {chapter_str} is live in the library.")


if __name__ == "__main__":
    main()
