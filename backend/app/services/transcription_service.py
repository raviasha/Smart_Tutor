import json
import logging
import re
import shutil
import sys
import subprocess
import tempfile
import os
from pathlib import Path
from typing import List, Optional, Tuple

import yt_dlp
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

openai_client = OpenAI(api_key=settings.openai_api_key)

# Resolve yt-dlp binary path from the same venv as the running Python
_VENV_BIN = Path(sys.executable).parent
_YT_DLP_BIN = str(_VENV_BIN / "yt-dlp")


def fetch_youtube_captions(video_id: str) -> Optional[List[dict]]:
    """
    Attempt to fetch YouTube captions using yt-dlp Python API.
    Returns a list of {start_time, end_time, text} dicts, or None if unavailable.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "subs")
            ydl_opts = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en"],
                "subtitlesformat": "json3",
                "outtmpl": output_path,
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Look for the downloaded subtitle file
            sub_file = None
            for f in os.listdir(tmpdir):
                if f.endswith(".json3"):
                    sub_file = os.path.join(tmpdir, f)
                    break

            if not sub_file:
                logger.info(f"No captions found for video {video_id}")
                return None

            with open(sub_file, "r", encoding="utf-8") as f:
                caption_data = json.load(f)

            return _parse_json3_captions(caption_data)

    except Exception as e:
        logger.error(f"Error fetching captions for {video_id}: {e}")
        return None


def _parse_json3_captions(data: dict) -> List[dict]:
    """Parse YouTube JSON3 caption format into our chunk format."""
    events = data.get("events", [])
    segments = []

    for event in events:
        if "segs" not in event:
            continue

        start_ms = event.get("tStartMs", 0)
        duration_ms = event.get("dDurationMs", 0)
        text_parts = []

        for seg in event["segs"]:
            text = seg.get("utf8", "").strip()
            if text and text != "\n":
                text_parts.append(text)

        if text_parts:
            segments.append({
                "start_time": start_ms / 1000.0,
                "end_time": (start_ms + duration_ms) / 1000.0,
                "text": " ".join(text_parts),
            })

    return _merge_into_chunks(segments) if segments else None


def transcribe_with_whisper(video_id: str) -> List[dict]:
    """
    Fallback: Download audio and transcribe with OpenAI Whisper API.
    Returns a list of {start_time, end_time, text} dicts.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "audio.mp3")

        # Download audio only using yt-dlp Python API
        logger.info(f"Downloading audio for {video_id}...")

        # Check if ffmpeg is available
        ffmpeg_path = shutil.which("ffmpeg")

        if ffmpeg_path:
            # ffmpeg available — extract and convert to mp3
            ydl_opts = {
                "format": "worstaudio/worst",
                "outtmpl": audio_path,
                "quiet": True,
                "no_warnings": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "9",
                }],
            }
        else:
            # No ffmpeg — download best available audio format directly
            logger.warning("ffmpeg not found, downloading raw audio (may be larger)")
            ydl_opts = {
                "format": "worstaudio/worst",
                "outtmpl": audio_path,
                "quiet": True,
                "no_warnings": True,
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            raise RuntimeError(f"Failed to download audio: {e}")

        # Find the actual output file (yt-dlp may change extension)
        actual_file = None
        for f in os.listdir(tmpdir):
            if f.startswith("audio"):
                actual_file = os.path.join(tmpdir, f)
                break

        if not actual_file or not os.path.exists(actual_file):
            raise RuntimeError("Audio file not found after download")

        # Check file size (Whisper API limit is 25MB)
        file_size_mb = os.path.getsize(actual_file) / (1024 * 1024)
        if file_size_mb > 25:
            raise RuntimeError(
                f"Audio file too large ({file_size_mb:.1f}MB). "
                "Whisper API supports up to 25MB. Try a shorter video."
            )

        # Transcribe with Whisper API
        logger.info(f"Transcribing audio for {video_id} with Whisper ({file_size_mb:.1f}MB)...")
        with open(actual_file, "rb") as audio_file:
            response = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        # Parse Whisper response into our format
        segments = []
        for segment in response.segments:
            segments.append({
                "start_time": segment["start"],
                "end_time": segment["end"],
                "text": segment["text"].strip(),
            })

        return _merge_into_chunks(segments)


def _merge_into_chunks(segments: List[dict], window_seconds: float = 30.0) -> List[dict]:
    """
    Merge small segments into larger chunks (~30 second windows).
    Respects sentence boundaries where possible.
    """
    if not segments:
        return []

    chunks = []
    current_chunk = {
        "start_time": segments[0]["start_time"],
        "end_time": segments[0]["end_time"],
        "text": segments[0]["text"],
    }

    for seg in segments[1:]:
        elapsed = seg["end_time"] - current_chunk["start_time"]
        text_so_far = current_chunk["text"]

        # Check if we should start a new chunk:
        # 1. Window exceeded AND current text ends with sentence boundary
        is_sentence_end = bool(re.search(r'[.!?]\s*$', text_so_far))

        if elapsed >= window_seconds and is_sentence_end:
            chunks.append(current_chunk)
            current_chunk = {
                "start_time": seg["start_time"],
                "end_time": seg["end_time"],
                "text": seg["text"],
            }
        else:
            current_chunk["end_time"] = seg["end_time"]
            current_chunk["text"] += " " + seg["text"]

    # Don't forget the last chunk
    chunks.append(current_chunk)
    return chunks


def get_transcript(video_id: str) -> Tuple[List[dict], str]:
    """
    Get transcript for a video. Tries YouTube captions first, falls back to Whisper.
    Returns (chunks, source) where source is 'youtube_captions' or 'whisper'.
    """
    # Step 1: Try YouTube captions (free)
    chunks = fetch_youtube_captions(video_id)
    if chunks:
        logger.info(f"Got YouTube captions for {video_id} ({len(chunks)} chunks)")
        return chunks, "youtube_captions"

    # Step 2: Fall back to Whisper (paid)
    logger.info(f"No YouTube captions for {video_id}, falling back to Whisper")
    chunks = transcribe_with_whisper(video_id)
    logger.info(f"Whisper transcribed {video_id} ({len(chunks)} chunks)")
    return chunks, "whisper"
