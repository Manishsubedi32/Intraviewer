-- Drop old tables (this will lose existing data)
DROP TABLE IF EXISTS video_frames CASCADE;
DROP TABLE IF EXISTS audio_chunks CASCADE;

-- Add JSONB columns to media_sessions
ALTER TABLE media_sessions 
ADD COLUMN IF NOT EXISTS audio_chunks JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS video_frames JSONB DEFAULT '[]'::jsonb;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_media_sessions_audio_chunks ON media_sessions USING GIN (audio_chunks);
CREATE INDEX IF NOT EXISTS idx_media_sessions_video_frames ON media_sessions USING GIN (video_frames);

-- Verify
SELECT 
    column_name, 
    data_type, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'media_sessions' 
AND column_name IN ('audio_chunks', 'video_frames');
