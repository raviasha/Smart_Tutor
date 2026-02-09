-- Smart Tutor Database Schema
-- Run this in Supabase Dashboard → SQL Editor → New Query

-- 1. Videos table
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    youtube_video_id VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(500),
    url VARCHAR(2048) NOT NULL,
    summary JSONB,
    status VARCHAR(20) DEFAULT 'processing' NOT NULL CHECK (status IN ('processing', 'ready', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 2. Transcript chunks table
CREATE TABLE IF NOT EXISTS transcript_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_transcript_chunks_video_time 
    ON transcript_chunks(video_id, start_time, end_time);

-- 3. QA History table
CREATE TABLE IF NOT EXISTS qa_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    video_timestamp FLOAT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_qa_history_user_video_time 
    ON qa_history(user_id, video_id, video_timestamp);

-- 4. Enable Row Level Security
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcript_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE qa_history ENABLE ROW LEVEL SECURITY;

-- 5. RLS Policies

-- Videos: anyone authenticated can read, service role can insert/update
CREATE POLICY "Anyone can read videos" ON videos
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage videos" ON videos
    FOR ALL USING (auth.role() = 'service_role');

-- Transcript chunks: anyone authenticated can read
CREATE POLICY "Anyone can read transcripts" ON transcript_chunks
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage transcripts" ON transcript_chunks
    FOR ALL USING (auth.role() = 'service_role');

-- QA History: users can only see their own, service role can manage all
CREATE POLICY "Users can read own QA" ON qa_history
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage QA" ON qa_history
    FOR ALL USING (auth.role() = 'service_role');
