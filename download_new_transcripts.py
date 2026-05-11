#!/usr/bin/env python3
"""Incremental Plaud-import: download alleen recordings die nog niet in PlaudTranscripts/ staan.

Scant ~/Documents/PlaudTranscripts/ voor bestaande file_ids (uit header `# File ID:`),
vergelijkt met Plaud cloud, downloadt alleen nieuwe.

Naming: <next_seq>_<safe_title>.txt (seq = max bestaand + 1 + offset)
"""

import json
import os
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from plaud_notes_mcp.plaud_client import PlaudClient

OUTPUT_DIR = Path.home() / "Documents" / "PlaudTranscripts"
OUTPUT_DIR.mkdir(exist_ok=True)


def safe_filename(title: str) -> str:
    safe = re.sub(r"[^\w\s\-]", "_", title)
    safe = re.sub(r"\s+", " ", safe).strip()
    return safe[:80]


def format_transcript(segments: list) -> str:
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


def download_transcript(client, http_client, file_id):
    try:
        raw = client._get(f"/file/detail/{file_id}")
        data = raw.get("data", {})
        for item in data.get("content_list", []):
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
    except Exception as e:
        return f"ERROR: {e}", None


def scan_existing_file_ids():
    """Scan PlaudTranscripts/ for already-downloaded file_ids."""
    existing = {}
    max_seq = 0
    for fp in OUTPUT_DIR.glob("*.txt"):
        m = re.match(r"^(\d+)_", fp.name)
        if m:
            seq = int(m.group(1))
            max_seq = max(max_seq, seq)
        try:
            with open(fp, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("# File ID:"):
                        fid = line.replace("# File ID:", "").strip()
                        if fid:
                            existing[fid] = fp.name
                        break
                    if not line.startswith("#"):
                        break
        except Exception:
            pass
    return existing, max_seq


def main():
    print(f"Output dir: {OUTPUT_DIR}")
    existing, max_seq = scan_existing_file_ids()
    print(f"Bestaande file_ids: {len(existing)}, max seq: {max_seq}")

    client = PlaudClient(region="eu")
    print(f"Listing cloud recordings (base_url={client._base_url})...")
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
    print(f"Cloud total: {len(all_recordings)}")

    # Filter: only new + has transcript + sort by date ASCENDING (oldest first)
    new_recordings = [r for r in all_recordings if r.file_id not in existing]
    # Sort oldest first so seq numbers stay chronologically ordered
    new_recordings.sort(key=lambda r: r.created_at if r.created_at else "")
    print(f"Nieuwe (niet in PlaudTranscripts/): {len(new_recordings)}")

    http_client = httpx.Client(timeout=30)
    succeeded = failed = no_transcript = 0

    for i, rec in enumerate(new_recordings, 1):
        seq = max_seq + i
        title = rec.filename or "Untitled"
        safe = safe_filename(title)
        filename = f"{seq:03d}_{safe}.txt"
        filepath = OUTPUT_DIR / filename
        print(f"[{i:3d}/{len(new_recordings)}] seq={seq} {title[:55]}...", end=" ", flush=True)

        transcript_text, _ = download_transcript(client, http_client, rec.file_id)

        if transcript_text and not transcript_text.startswith("ERROR"):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n")
                f.write(f"# File ID: {rec.file_id}\n")
                f.write(f"# Duration: {rec.duration_str}\n")
                if rec.created_at:
                    f.write(f"# Date: {rec.created_at.isoformat()}\n")
                f.write("# ---\n\n")
                f.write(transcript_text)
            succeeded += 1
            print(f"OK ({len(transcript_text)} chars)")
        elif transcript_text.startswith("ERROR"):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n# File ID: {rec.file_id}\n# {transcript_text}\n")
            failed += 1
            print(f"FAILED: {transcript_text[:60]}")
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n# File ID: {rec.file_id}\n# No transcript available\n")
            no_transcript += 1
            print("No transcript")

    http_client.close()
    client.close()
    print(f"\nDONE: {succeeded} OK, {no_transcript} no transcript, {failed} failed")


if __name__ == "__main__":
    main()
