import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.auth import get_current_user
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


@router.get("/{video_id}")
async def get_transcript(
    video_id: UUID,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Get the full transcript for a video."""
    result = (
        db.table("transcript_chunks")
        .select("*")
        .eq("video_id", str(video_id))
        .order("start_time")
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Transcript not found for this video")

    return {
        "video_id": str(video_id),
        "chunks": result.data,
    }


@router.get("/{video_id}/window")
async def get_transcript_window(
    video_id: UUID,
    timestamp: float,
    window_before: float = 60.0,
    window_after: float = 30.0,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Get transcript chunks within a time window around a timestamp."""
    start = max(0, timestamp - window_before)
    end = timestamp + window_after

    result = (
        db.table("transcript_chunks")
        .select("*")
        .eq("video_id", str(video_id))
        .gte("end_time", start)
        .lte("start_time", end)
        .order("start_time")
        .execute()
    )

    return {
        "video_id": str(video_id),
        "timestamp": timestamp,
        "window": {"start": start, "end": end},
        "chunks": result.data,
    }
