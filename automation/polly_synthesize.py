#!/usr/bin/env python3
"""
polly_synthesize.py -- Phase 2a automation

Replaces the manual Amazon Polly console workflow: sign into AWS, paste
SSML, "Synthesize to S3", wait, download, delete from S3. This does the
same thing via boto3's async long-form synthesis API (StartSpeechSynthesisTask),
which is required (rather than the simple real-time SynthesizeSpeech call)
because chapter-length SSML exceeds the real-time API's size limit.

Voice/engine match the project convention: Neural engine, Brian (English
British).

Requires:
    pip install boto3 --break-system-packages
    AWS credentials available via environment variables or a profile:
        AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
    An IAM user/role scoped to just Polly (StartSpeechSynthesisTask,
    GetSpeechSynthesisTask) and S3 (PutObject/GetObject/DeleteObject) on
    the rex-file-storage-2026 bucket is enough -- no need for broader access.

Usage:
    python3 polly_synthesize.py chapter-v1.ssml chapter.mp3
    python3 polly_synthesize.py chapter-v1.ssml chapter.mp3 --bucket rex-file-storage-2026 --region us-east-1
"""

import argparse
import sys
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="Synthesize an SSML chapter to mp3 via Amazon Polly.")
    ap.add_argument("ssml_file", help="Path to the V1 SSML file (verse numbers stripped)")
    ap.add_argument("output_mp3", help="Local path to save the resulting mp3")
    ap.add_argument("--bucket", default="rex-file-storage-2026", help="S3 bucket used as the synthesis output target")
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--voice", default="Brian")
    ap.add_argument("--engine", default="neural")
    ap.add_argument("--language-code", default="en-GB")
    ap.add_argument("--keep-s3-copy", action="store_true", help="Don't delete the object from S3 after downloading (it's deleted by default to avoid storage charges)")
    ap.add_argument("--poll-interval", type=float, default=5.0, help="Seconds between task status checks")
    ap.add_argument("--timeout", type=float, default=600.0, help="Max seconds to wait for synthesis to complete")
    args = ap.parse_args()

    try:
        import boto3
    except ImportError:
        print("ERROR: boto3 is not installed. Run: pip install boto3 --break-system-packages", file=sys.stderr)
        sys.exit(1)

    ssml_path = Path(args.ssml_file)
    ssml_text = ssml_path.read_text(encoding="utf-8", errors="replace")

    polly = boto3.client("polly", region_name=args.region)
    s3 = boto3.client("s3", region_name=args.region)

    print(f"Starting Polly synthesis task ({args.engine} engine, {args.voice} voice)...")
    resp = polly.start_speech_synthesis_task(
        Engine=args.engine,
        LanguageCode=args.language_code,
        OutputFormat="mp3",
        OutputS3BucketName=args.bucket,
        Text=ssml_text,
        TextType="ssml",
        VoiceId=args.voice,
    )
    task = resp["SynthesisTask"]
    task_id = task["TaskId"]
    print(f"Task ID: {task_id}")

    deadline = time.time() + args.timeout
    output_uri = None
    while time.time() < deadline:
        status_resp = polly.get_speech_synthesis_task(TaskId=task_id)
        task = status_resp["SynthesisTask"]
        status = task["TaskStatus"]
        if status == "completed":
            output_uri = task["OutputUri"]
            break
        if status == "failed":
            reason = task.get("TaskStatusReason", "unknown reason")
            print(f"ERROR: Polly synthesis failed: {reason}", file=sys.stderr)
            sys.exit(1)
        print(f"  status: {status} -- waiting {args.poll_interval:.0f}s...")
        time.sleep(args.poll_interval)
    else:
        print("ERROR: Timed out waiting for Polly synthesis to complete.", file=sys.stderr)
        sys.exit(1)

    # OutputUri looks like: https://s3.<region>.amazonaws.com/<bucket>/<key>
    key = output_uri.split(f"{args.bucket}/", 1)[-1]
    print(f"Synthesis complete. Downloading s3://{args.bucket}/{key} ...")

    output_path = Path(args.output_mp3)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(args.bucket, key, str(output_path))
    print(f"Wrote: {output_path}")

    if not args.keep_s3_copy:
        s3.delete_object(Bucket=args.bucket, Key=key)
        print(f"Deleted s3://{args.bucket}/{key} (avoids ongoing storage charges)")

    print("Done.")


if __name__ == "__main__":
    main()
