import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, Text, Enum, DateTime, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    youtube_video_id = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=True)
    url = Column(String(2048), nullable=False)
    summary = Column(JSON, nullable=True)  # {topic, level, key_concepts, paragraph}
    status = Column(
        Enum("processing", "ready", "failed", name="video_status"),
        default="processing",
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    transcript_chunks = relationship("TranscriptChunk", back_populates="video", cascade="all, delete-orphan")
    qa_history = relationship("QAHistory", back_populates="video", cascade="all, delete-orphan")


class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(Float, nullable=False)  # seconds
    end_time = Column(Float, nullable=False)  # seconds
    text = Column(Text, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="transcript_chunks")

    __table_args__ = (
        Index("ix_transcript_chunks_video_time", "video_id", "start_time", "end_time"),
    )


class QAHistory(Base):
    __tablename__ = "qa_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # From Supabase Auth
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    video_timestamp = Column(Float, nullable=False)  # seconds into the video
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="qa_history")

    __table_args__ = (
        Index("ix_qa_history_user_video_time", "user_id", "video_id", "video_timestamp"),
    )
