import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from supabase import Client

from app.core.auth import get_current_user
from app.core.database import get_supabase, supabase as supabase_admin
from app.schemas.schemas import (
    VideoSubmitRequest,
    VideoResponse,
    VideoStatusResponse,
)
from app.services.youtube_service import validate_video
from app.services.transcription_service import get_transcript
from app.services.ai_service import generate_video_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])


def _process_video(video_id: str, youtube_video_id: str, title: str):
    """
    Background task to process a video:
    1. Get transcript (captions or Whisper)
    2. Store transcript chunks
    3. Generate summary
    4. Update video status
    """
    try:
        # Get transcript
        chunks, source = get_transcript(youtube_video_id)
        logger.info(f"Transcript for {youtube_video_id}: {len(chunks)} chunks via {source}")

        # Store transcript chunks
        chunk_records = [
            {
                "video_id": video_id,
                "start_time": chunk["start_time"],
                "end_time": chunk["end_time"],
                "text": chunk["text"],
            }
            for chunk in chunks
        ]
        # Insert in batches of 100
        for i in range(0, len(chunk_records), 100):
            batch = chunk_records[i : i + 100]
            supabase_admin.table("transcript_chunks").insert(batch).execute()

        # Generate summary
        summary = generate_video_summary(chunks, title)
        logger.info(f"Summary generated for {youtube_video_id}")

        # Update video status
        supabase_admin.table("videos").update(
            {"summary": summary, "status": "ready"}
        ).eq("id", video_id).execute()

    except Exception as e:
        logger.error(f"Failed to process video {youtube_video_id}: {e}")
        supabase_admin.table("videos").update(
            {"status": "failed"}
        ).eq("id", video_id).execute()


@router.post("/")
async def submit_video(
    request: VideoSubmitRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """
    Submit a YouTube video URL for processing.
    If the video has already been processed, returns the existing record.
    Otherwise, starts background processing and returns immediately.
    """
    # Validate the URL and extract video ID
    try:
        youtube_video_id, metadata = validate_video(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check if video already exists
    existing = (
        db.table("videos")
        .select("*")
        .eq("youtube_video_id", youtube_video_id)
        .execute()
    )
    if existing.data:
        video = existing.data[0]
        # If previously failed, allow retry
        if video["status"] == "failed":
            db.table("videos").update({"status": "processing"}).eq("id", video["id"]).execute()
            # Clean up old transcript chunks if any
            db.table("transcript_chunks").delete().eq("video_id", video["id"]).execute()
            background_tasks.add_task(
                _process_video,
                video["id"],
                youtube_video_id,
                video["title"],
            )
            video["status"] = "processing"
        return video

    # Create new video record
    video_data = {
        "youtube_video_id": youtube_video_id,
        "title": metadata.get("title", "Unknown Title"),
        "url": request.url,
        "status": "processing",
    }
    result = db.table("videos").insert(video_data).execute()
    video = result.data[0]

    # Start background processing
    background_tasks.add_task(
        _process_video,
        video["id"],
        youtube_video_id,
        video["title"],
    )

    return video


@router.get("/{video_id}/status")
async def get_video_status(
    video_id: UUID,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Check the processing status of a video."""
    result = db.table("videos").select("id, youtube_video_id, status").eq("id", str(video_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Video not found")
    return result.data[0]


@router.get("/{video_id}")
async def get_video(
    video_id: UUID,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Get full video details including summary."""
    result = db.table("videos").select("*").eq("id", str(video_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Video not found")
    return result.data[0]
