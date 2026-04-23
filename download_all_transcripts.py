#!/usr/bin/env python3
"""Download all Plaud Notes transcripts to local text files."""

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from plaud_notes_mcp.plaud_client import PlaudClient

OUTPUT_DIR = "/Users/christian/Documents/PlaudTranscripts"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def safe_filename(title: str) -> str:
    """Convert title to a safe filename."""
    safe = re.sub(r'[^\w\s\-]', '_', title)
    safe = re.sub(r'\s+', ' ', safe).strip()
    return safe[:80]


def format_transcript(segments: list) -> str:
    """Format transcript segments into readable text with speaker labels."""
    lines = []
    current_speaker = None
    for seg in segments:
        speaker = seg.get("speaker", seg.get("spk", ""))
        text = seg.get("content", seg.get("text", ""))
        if not text:
            continue
        if speaker and speaker != current_speaker:
            current_speaker = speaker
            lines.append(f"\n[{current_speaker}]")
        lines.append(text)
    return "\n".join(lines).strip()


def download_transcript(client: PlaudClient, http_client: httpx.Client, file_id: str) -> tuple[str, list | None]:
    """Download transcript for a single recording. Returns (transcript_text, segments)."""
    try:
        raw = client._get(f"/file/detail/{file_id}")
        data = raw.get("data", {})
        content_list = data.get("content_list", [])

        for item in content_list:
            if item.get("data_type") == "transaction" and item.get("task_status") == 1:
                url = item.get("data_link", "")
                if not url:
                    continue
                resp = http_client.get(url, timeout=30)
                resp.raise_for_status()
                segments = resp.json()
                if segments:
                    return format_transcript(segments), segments
                return "", None

        # Also check pre_download_content_list for summary
        return "", None
    except Exception as e:
        return f"ERROR: {e}", None


def main():
    client = PlaudClient()

    # List all recordings
    print("Listing all recordings...")
    all_recordings = []
    skip = 0
    while True:
        batch = client.list_recordings(limit=500, skip=skip, sort_by="start_time")
        if not batch:
            break
        all_recordings.extend(batch)
        if len(batch) < 500:
            break
        skip += len(batch)

    print(f"Found {len(all_recordings)} recordings")

    http_client = httpx.Client(timeout=30)
    succeeded = 0
    failed = 0
    no_transcript = 0

    # Process all recordings
    for i, rec in enumerate(all_recordings, 1):
        title = rec.filename or "Untitled"
        safe_title = safe_filename(title)
        filename = f"{i:03d}_{safe_title}.txt"
        filepath = os.path.join(OUTPUT_DIR, filename)

        print(f"[{i:3d}/{len(all_recordings)}] {title[:60]}...", end=" ", flush=True)

        transcript_text, segments = download_transcript(client, http_client, rec.file_id)

        if transcript_text and not transcript_text.startswith("ERROR"):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n")
                f.write(f"# File ID: {rec.file_id}\n")
                f.write(f"# Duration: {rec.duration_str}\n")
                if rec.created_at:
                    f.write(f"# Date: {rec.created_at.isoformat()}\n")
                f.write(f"# ---\n\n")
                f.write(transcript_text)
            succeeded += 1
            print(f"OK ({len(transcript_text)} chars)")
        elif transcript_text.startswith("ERROR"):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n# {transcript_text}\n")
            failed += 1
            print(f"FAILED: {transcript_text[:80]}")
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n# No transcript available\n")
            no_transcript += 1
            print("No transcript")

    http_client.close()
    client.close()

    print(f"\n{'='*60}")
    print(f"DONE: {succeeded} succeeded, {no_transcript} no transcript, {failed} failed")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
