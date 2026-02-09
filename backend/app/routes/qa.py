import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from supabase import Client

from app.core.auth import get_current_user
from app.core.database import get_supabase, supabase as supabase_admin
from app.services.ai_service import build_context, answer_question, answer_question_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask")
async def ask_question_endpoint(
    request: dict,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """
    Ask a question about a video at a specific timestamp.
    Returns a context-aware AI answer.
    """
    user_id = user["id"]
    video_id = request.get("video_id")
    timestamp = request.get("timestamp", 0)
    question = request.get("question", "")

    if not video_id or not question:
        raise HTTPException(status_code=400, detail="video_id and question are required")

    # Get the video
    video_result = db.table("videos").select("*").eq("id", video_id).execute()
    if not video_result.data:
        raise HTTPException(status_code=404, detail="Video not found")
    video = video_result.data[0]

    if video["status"] != "ready":
        raise HTTPException(status_code=400, detail="Video is still being processed")

    # Get transcript chunks for context window
    window_start = max(0, timestamp - 60)
    window_end = timestamp + 30

    chunks_result = (
        db.table("transcript_chunks")
        .select("*")
        .eq("video_id", video_id)
        .gte("end_time", window_start)
        .lte("start_time", window_end)
        .order("start_time")
        .execute()
    )

    chunks_data = [
        {"start_time": c["start_time"], "end_time": c["end_time"], "text": c["text"]}
        for c in chunks_result.data
    ]

    # Get previous Q&A history for this user on this video
    qa_result = (
        db.table("qa_history")
        .select("*")
        .eq("user_id", user_id)
        .eq("video_id", video_id)
        .order("created_at")
        .execute()
    )

    qa_data = [
        {"video_timestamp": qa["video_timestamp"], "question": qa["question"], "answer": qa["answer"]}
        for qa in qa_result.data
    ]

    # Build context
    context = build_context(
        summary=video.get("summary"),
        transcript_chunks=chunks_data,
        timestamp=timestamp,
        qa_history=qa_data,
    )

    # Get AI answer
    try:
        answer = answer_question(context, question)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Store Q&A in history
    qa_entry = {
        "user_id": user_id,
        "video_id": video_id,
        "video_timestamp": timestamp,
        "question": question,
        "answer": answer,
    }
    result = db.table("qa_history").insert(qa_entry).execute()

    return result.data[0]


@router.post("/ask/stream")
async def ask_question_stream_endpoint(
    request: dict,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """
    Ask a question and stream the AI answer via Server-Sent Events (SSE).
    The full answer is saved to the database after streaming completes.
    """
    user_id = user["id"]
    video_id = request.get("video_id")
    timestamp = request.get("timestamp", 0)
    question = request.get("question", "")

    if not video_id or not question:
        raise HTTPException(status_code=400, detail="video_id and question are required")

    # Get the video
    video_result = db.table("videos").select("*").eq("id", video_id).execute()
    if not video_result.data:
        raise HTTPException(status_code=404, detail="Video not found")
    video = video_result.data[0]

    if video["status"] != "ready":
        raise HTTPException(status_code=400, detail="Video is still being processed")

    # Get transcript chunks for context window
    window_start = max(0, timestamp - 60)
    window_end = timestamp + 30

    chunks_result = (
        db.table("transcript_chunks")
        .select("*")
        .eq("video_id", video_id)
        .gte("end_time", window_start)
        .lte("start_time", window_end)
        .order("start_time")
        .execute()
    )

    chunks_data = [
        {"start_time": c["start_time"], "end_time": c["end_time"], "text": c["text"]}
        for c in chunks_result.data
    ]

    # Get previous Q&A
    qa_result = (
        db.table("qa_history")
        .select("*")
        .eq("user_id", user_id)
        .eq("video_id", video_id)
        .order("created_at")
        .execute()
    )

    qa_data = [
        {"video_timestamp": qa["video_timestamp"], "question": qa["question"], "answer": qa["answer"]}
        for qa in qa_result.data
    ]

    # Build context
    context = build_context(
        summary=video.get("summary"),
        transcript_chunks=chunks_data,
        timestamp=timestamp,
        qa_history=qa_data,
    )

    # Stream response
    full_answer_parts = []

    async def event_generator():
        async for chunk in answer_question_stream(context, question):
            full_answer_parts.append(chunk)
            yield f"data: {json.dumps({'text': chunk})}\n\n"

        # Save complete answer to DB
        full_answer = "".join(full_answer_parts)
        qa_entry = {
            "user_id": user_id,
            "video_id": video_id,
            "video_timestamp": timestamp,
            "question": question,
            "answer": full_answer,
        }
        result = supabase_admin.table("qa_history").insert(qa_entry).execute()

        yield f"data: {json.dumps({'done': True, 'qa_id': result.data[0]['id']})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/history/{video_id}")
async def get_qa_history(
    video_id: UUID,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Get all Q&A history for a user on a specific video."""
    user_id = user["id"]

    result = (
        db.table("qa_history")
        .select("*")
        .eq("user_id", user_id)
        .eq("video_id", str(video_id))
        .order("created_at")
        .execute()
    )

    return {
        "video_id": str(video_id),
        "history": result.data,
    }
