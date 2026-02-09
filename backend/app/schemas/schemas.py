from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ---- Video Schemas ----

class VideoSubmitRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")


class VideoSummary(BaseModel):
    title: str
    topic: str
    level: str  # beginner / intermediate / advanced
    key_concepts: List[str]
    paragraph: str


class VideoResponse(BaseModel):
    id: UUID
    youtube_video_id: str
    title: Optional[str]
    url: str
    summary: Optional[VideoSummary]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class VideoStatusResponse(BaseModel):
    id: UUID
    youtube_video_id: str
    status: str


# ---- Transcript Schemas ----

class TranscriptChunkResponse(BaseModel):
    id: UUID
    start_time: float
    end_time: float
    text: str

    class Config:
        from_attributes = True


class TranscriptResponse(BaseModel):
    video_id: UUID
    chunks: List[TranscriptChunkResponse]


# ---- Q&A Schemas ----

class AskQuestionRequest(BaseModel):
    video_id: UUID
    timestamp: float = Field(..., ge=0, description="Timestamp in seconds where the user paused")
    question: str = Field(..., min_length=1, max_length=2000)


class QAResponse(BaseModel):
    id: UUID
    video_id: UUID
    video_timestamp: float
    question: str
    answer: str
    created_at: datetime

    class Config:
        from_attributes = True


class QAHistoryResponse(BaseModel):
    video_id: UUID
    history: List[QAResponse]
