-- Migration: Add JSONB columns to media_sessions table
-- This consolidates audio_chunks and video_frames into single row per session

-- Add JSONB columns to media_sessions
ALTER TABLE media_sessions 
ADD COLUMN IF NOT EXISTS audio_chunks JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS video_frames JSONB DEFAULT '[]'::jsonb;

-- Optional: Migrate existing data from audio_chunks table (if exists)
-- Uncomment if you want to preserve existing data:
/*
UPDATE media_sessions ms
SET audio_chunks = (
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'chunk_index', ac.chunk_index,
            'file_path', ac.file_path,
            'file_size', ac.file_size,
            'mime_type', ac.mime_type,
            'start_timestamp', ac.start_timestamp,
            'end_timestamp', ac.end_timestamp,
            'duration_ms', ac.duration_ms,
            'transcription', ac.transcription,
            'processed', ac.processed
        ) ORDER BY ac.chunk_index
    ), '[]'::jsonb)
    FROM audio_chunks ac
    WHERE ac.media_session_id = ms.id
);
*/

-- Optional: Migrate existing data from video_frames table (if exists)
/*
UPDATE media_sessions ms
SET video_frames = (
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'frame_index', vf.frame_index,
            'chunk_index', vf.chunk_index,
            'file_path', vf.file_path,
            'file_size', vf.file_size,
            'mime_type', vf.mime_type,
            'timestamp', vf.timestamp,
            'offset_ms', vf.offset_ms,
            'processed', vf.processed,
            'analysis', vf.analysis
        ) ORDER BY vf.frame_index
    ), '[]'::jsonb)
    FROM video_frames vf
    WHERE vf.media_session_id = ms.id
);
*/

-- Optional: Drop old tables after migration (BE CAREFUL!)
-- Only run this after confirming data is migrated and system works
-- DROP TABLE IF EXISTS audio_chunks;
-- DROP TABLE IF EXISTS video_frames;

-- Create indexes for better JSONB query performance
CREATE INDEX IF NOT EXISTS idx_media_sessions_audio_chunks ON media_sessions USING GIN (audio_chunks);
CREATE INDEX IF NOT EXISTS idx_media_sessions_video_frames ON media_sessions USING GIN (video_frames);

-- Verify migration
SELECT 
    id, 
    session_id, 
    jsonb_array_length(COALESCE(audio_chunks, '[]'::jsonb)) as num_audio_chunks,
    jsonb_array_length(COALESCE(video_frames, '[]'::jsonb)) as num_video_frames
FROM media_sessions
LIMIT 10;
