import re
import logging
from typing import Optional, Tuple

import yt_dlp

logger = logging.getLogger(__name__)

# Regex patterns for YouTube URLs
YOUTUBE_PATTERNS = [
    r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
]


def extract_video_id(url: str) -> Optional[str]:
    """Extract the YouTube video ID from various URL formats."""
    for pattern in YOUTUBE_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_video_metadata(video_id: str) -> dict:
    """
    Fetch video metadata (title, duration, etc.) using yt-dlp.
    Does NOT download the video.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", "Unknown Title"),
                "duration": info.get("duration", 0),
                "description": info.get("description", ""),
                "uploader": info.get("uploader", ""),
                "is_live": info.get("is_live", False),
                "availability": info.get("availability", "public"),
            }
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if "private" in error_msg:
            raise ValueError("This video is private and cannot be accessed.")
        elif "age" in error_msg:
            raise ValueError("This video is age-restricted and cannot be processed.")
        elif "unavailable" in error_msg or "not available" in error_msg:
            raise ValueError("This video is unavailable.")
        else:
            raise ValueError(f"Unable to access this video: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to fetch metadata for video {video_id}: {e}")
        raise ValueError(f"Failed to fetch video information: {str(e)}")


def validate_video(url: str) -> Tuple[str, dict]:
    """
    Validate a YouTube URL and return (video_id, metadata).
    Raises ValueError if URL is invalid or video is inaccessible.
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(
            "Invalid YouTube URL. Please provide a valid YouTube video link."
        )

    metadata = get_video_metadata(video_id)

    if metadata.get("is_live"):
        raise ValueError("Live videos are not supported. Please use a recorded video.")

    duration = metadata.get("duration", 0)
    if duration > 3 * 3600:  # > 3 hours
        logger.warning(f"Long video submitted: {video_id} ({duration}s)")
        # We still allow it but log a warning

    return video_id, metadata
