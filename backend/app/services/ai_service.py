import logging
from typing import List, Optional, AsyncGenerator

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

openai_client = OpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a patient, clear tutor helping a student understand a video. \
Use the provided transcript context to ground your answers. Reference what was being \
explained at the relevant moment. Use simple, learner-friendly language. \
If the transcript doesn't contain enough information to answer, say so honestly. \
Do not make up information that isn't in the transcript context."""

SUMMARY_PROMPT = """Analyze the following video transcript and produce a structured summary in JSON format.

The JSON should have these exact fields:
- "topic": A single sentence describing the main topic
- "level": One of "beginner", "intermediate", or "advanced"
- "key_concepts": An array of 5-10 key concepts/ideas covered
- "paragraph": A 3-5 sentence summary of the video content

Transcript:
{transcript}

Respond with ONLY valid JSON, no other text."""


def generate_video_summary(transcript_chunks: List[dict], title: str) -> dict:
    """
    Generate a one-time summary for a video using GPT-4o-mini.
    Uses the transcript (or first 15 min for long videos).
    """
    # Build transcript text (limit to first 15 min for very long videos)
    transcript_text = ""
    for chunk in transcript_chunks:
        if chunk["start_time"] > 900:  # 15 minutes
            transcript_text += "\n[... transcript continues ...]"
            break
        start = _format_time(chunk["start_time"])
        end = _format_time(chunk["end_time"])
        transcript_text += f"[{start}-{end}] {chunk['text']}\n"

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes educational video transcripts."},
                {"role": "user", "content": SUMMARY_PROMPT.format(transcript=transcript_text)},
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        import json
        summary = json.loads(response.choices[0].message.content)
        summary["title"] = title
        return summary

    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        return {
            "title": title,
            "topic": "Unable to generate summary",
            "level": "unknown",
            "key_concepts": [],
            "paragraph": "Summary generation failed. The video can still be used for Q&A.",
        }


def build_context(
    summary: dict,
    transcript_chunks: List[dict],
    timestamp: float,
    qa_history: List[dict],
) -> str:
    """
    Assemble the context package for the AI answering a question.

    Includes:
    1. Video summary (~200 tokens)
    2. Transcript window: T-60s to T+30s
    3. Nearby Q&A history (last 5 within ±5 min)
    """
    context_parts = []

    # 1. Video summary
    if summary:
        context_parts.append(f"=== VIDEO SUMMARY ===")
        context_parts.append(f"Title: {summary.get('title', 'Unknown')}")
        context_parts.append(f"Topic: {summary.get('topic', 'Unknown')}")
        context_parts.append(f"Level: {summary.get('level', 'Unknown')}")
        key_concepts = summary.get("key_concepts", [])
        if key_concepts:
            context_parts.append(f"Key concepts: {', '.join(key_concepts)}")
        context_parts.append(f"Summary: {summary.get('paragraph', '')}")
        context_parts.append("")

    # 2. Transcript window (T-60s to T+30s)
    window_start = max(0, timestamp - 60)
    window_end = timestamp + 30

    relevant_chunks = [
        c for c in transcript_chunks
        if c["end_time"] >= window_start and c["start_time"] <= window_end
    ]

    if relevant_chunks:
        context_parts.append(f"=== TRANSCRIPT (around {_format_time(timestamp)}) ===")
        for chunk in relevant_chunks:
            start = _format_time(chunk["start_time"])
            end = _format_time(chunk["end_time"])
            marker = " <<<< YOU ARE HERE" if chunk["start_time"] <= timestamp <= chunk["end_time"] else ""
            context_parts.append(f"[{start}-{end}] {chunk['text']}{marker}")
        context_parts.append("")

    # 3. Nearby Q&A history (within ±5 min, max 5)
    if qa_history:
        nearby_qa = [
            qa for qa in qa_history
            if abs(qa["video_timestamp"] - timestamp) <= 300  # ±5 min
        ]
        nearby_qa = nearby_qa[-5:]  # last 5

        if nearby_qa:
            context_parts.append("=== PREVIOUS Q&A (this session) ===")
            for qa in nearby_qa:
                t = _format_time(qa["video_timestamp"])
                context_parts.append(f"[{t}] Q: {qa['question']}")
                # Truncate long answers in context
                answer = qa["answer"]
                if len(answer) > 300:
                    answer = answer[:300] + "..."
                context_parts.append(f"[{t}] A: {answer}")
            context_parts.append("")

    return "\n".join(context_parts)


def answer_question(context: str, question: str) -> str:
    """
    Send the context and question to GPT-4o-mini and return the answer.
    Non-streaming version for simple use.
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nStudent's question: {question}"},
            ],
            temperature=0.5,
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM answering failed: {e}")
        raise RuntimeError(f"Failed to generate answer: {str(e)}")


async def answer_question_stream(context: str, question: str) -> AsyncGenerator[str, None]:
    """
    Stream the answer from GPT-4o-mini using SSE.
    Yields chunks of text as they arrive.
    """
    try:
        stream = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nStudent's question: {question}"},
            ],
            temperature=0.5,
            max_tokens=800,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        logger.error(f"LLM streaming failed: {e}")
        yield f"\n\n[Error: Failed to generate answer. Please try again.]"


def _format_time(seconds: float) -> str:
    """Format seconds to MM:SS string."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"
