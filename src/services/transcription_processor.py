"""
Background Audio Transcription Processor

Processes saved audio chunks asynchronously and updates database with transcripts.
Runs as a background task to avoid blocking the WebSocket ingestion.
"""

import logging
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from src.services.transcription import transcribe_audio_chunk
from src.models.models import AudioChunk, MediaSession

logger = logging.getLogger(__name__)


async def process_audio_chunk_transcription(
    db: Session,
    session_id: str,
    chunk_index: int,
    file_path: str,
    language: Optional[str] = "en"
):
    """
    Process transcription for a single audio chunk.
    
    This function:
    1. Calls faster-whisper to transcribe the audio
    2. Updates the MediaSession's audio_chunks JSONB array with the transcript
    3. Handles errors gracefully
    
    Args:
        db: Database session
        session_id: Media session UUID
        chunk_index: Chunk sequence number
        file_path: Path to the audio file
        language: Language code (default: "en")
    """
    try:
        logger.info(f"🎯 Starting transcription: session_id={session_id}, chunk={chunk_index}, file={file_path}")
        
        # Check if file exists
        if not Path(file_path).exists():
            logger.error(f"❌ Audio file not found: {file_path}")
            return
        
        # Run transcription
        result = await transcribe_audio_chunk(
            audio_path=file_path,
            session_id=session_id,
            chunk_index=chunk_index,
            language=language
        )
        
        # Update MediaSession's audio_chunks JSONB array
        media_session = db.query(MediaSession).filter(MediaSession.session_id == session_id).first()
        
        if media_session and media_session.audio_chunks is not None:
            # Find the chunk in the array and update it
            for chunk in media_session.audio_chunks:
                if chunk.get("chunk_index") == chunk_index:
                    chunk["transcription"] = result["full_text"]
                    chunk["processed"] = True
                    break
            
            # Trigger SQLAlchemy to detect the change
            from sqlalchemy.orm.attributes import flag_modified
            media_session.audio_chunks = media_session.audio_chunks.copy()
            flag_modified(media_session, "audio_chunks")
            
            db.commit()
            
            logger.info(
                f"✅ Transcription saved: session_id={session_id}, chunk={chunk_index}, "
                f"text_length={len(result['full_text'])}, "
                f"segments={len(result['segments'])}"
            )
        else:
            logger.error(f"❌ MediaSession not found or audio_chunks empty: session_id={session_id}")
    
    except Exception as e:
        logger.error(
            f"❌ Transcription processing failed: "
            f"session_id={session_id}, chunk={chunk_index}, error={str(e)}"
        )
        
        # Mark as failed (but still processed to avoid retry loops)
        try:
            media_session = db.query(MediaSession).filter(MediaSession.session_id == session_id).first()
            if media_session and media_session.audio_chunks is not None:
                for chunk in media_session.audio_chunks:
                    if chunk.get("chunk_index") == chunk_index:
                        chunk["processed"] = True
                        chunk["transcription"] = f"[Transcription failed: {str(e)}]"
                        break
                
                media_session.audio_chunks = media_session.audio_chunks.copy()
                db.commit()
        except Exception as db_error:
            logger.error(f"❌ Failed to update database: {db_error}")


async def process_pending_transcriptions(db: Session):
    """
    Process all pending audio chunks that haven't been transcribed yet.
    
    This can be called:
    - On application startup to catch up
    - Periodically via a scheduled task
    - Manually via an admin endpoint
    
    Args:
        db: Database session
    """
    try:
        # Find all media sessions with unprocessed audio chunks
        media_sessions = db.query(MediaSession).filter(
            MediaSession.audio_chunks.isnot(None)
        ).all()
        
        pending_count = 0
        
        for media_session in media_sessions:
            if not media_session.audio_chunks:
                continue
            
            for chunk in media_session.audio_chunks:
                if not chunk.get("processed", False) and not chunk.get("transcription"):
                    pending_count += 1
                    
                    await process_audio_chunk_transcription(
                        db=db,
                        session_id=media_session.session_id,
                        chunk_index=chunk["chunk_index"],
                        file_path=chunk["file_path"],
                        language="en"
                    )
        
        if pending_count == 0:
            logger.info("✅ No pending transcriptions")
        else:
            logger.info(f"📋 Processed {pending_count} pending transcriptions")
    
    except Exception as e:
        logger.error(f"❌ Error processing pending transcriptions: {e}")
