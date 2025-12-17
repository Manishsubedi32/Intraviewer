"""
Transcription Management Endpoints

Admin/utility endpoints for managing transcription processing.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from src.db.database import get_db
from src.models.models import AudioChunk, MediaSession
from src.services.transcription_processor import (
    process_audio_chunk_transcription,
    process_pending_transcriptions
)

router = APIRouter(prefix="/transcription", tags=["transcription"])


# ============================================
# Response Models
# ============================================

class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str
    confidence: Optional[float] = None


class AudioChunkTranscription(BaseModel):
    id: int
    chunk_index: int
    file_path: str
    transcription: Optional[str]
    processed: bool
    
    class Config:
        from_attributes = True


class TranscriptionStatus(BaseModel):
    total_chunks: int
    transcribed: int
    pending: int
    failed: int


# ============================================
# Endpoints
# ============================================

@router.get("/status/{session_id}", response_model=TranscriptionStatus)
async def get_transcription_status(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get transcription status for a media session.
    
    Returns count of total/transcribed/pending chunks.
    """
    media_session = db.query(MediaSession).filter(
        MediaSession.session_id == session_id
    ).first()
    
    if not media_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    chunks = media_session.audio_chunks or []
    
    total = len(chunks)
    transcribed = sum(1 for c in chunks if c.get("processed") and c.get("transcription") and not c["transcription"].startswith("[Transcription failed"))
    failed = sum(1 for c in chunks if c.get("processed") and c.get("transcription") and c["transcription"].startswith("[Transcription failed"))
    pending = total - transcribed - failed
    
    return TranscriptionStatus(
        total_chunks=total,
        transcribed=transcribed,
        pending=pending,
        failed=failed
    )


@router.get("/chunks/{session_id}")
async def get_session_transcriptions(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all audio chunks and their transcriptions for a session.
    
    Returns list of chunks with transcription text.
    """
    media_session = db.query(MediaSession).filter(
        MediaSession.session_id == session_id
    ).first()
    
    if not media_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    chunks = media_session.audio_chunks or []
    
    # Sort by chunk_index
    sorted_chunks = sorted(chunks, key=lambda x: x.get("chunk_index", 0))
    
    return sorted_chunks


@router.get("/full-text/{session_id}")
async def get_full_transcript(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get complete concatenated transcript for a session.
    
    Returns all transcribed text in order.
    """
    media_session = db.query(MediaSession).filter(
        MediaSession.session_id == session_id
    ).first()
    
    if not media_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    chunks = media_session.audio_chunks or []
    
    # Sort by chunk_index and filter processed chunks
    sorted_chunks = sorted(chunks, key=lambda x: x.get("chunk_index", 0))
    processed_chunks = [
        c for c in sorted_chunks 
        if c.get("processed") and c.get("transcription") and not c["transcription"].startswith("[Transcription failed")
    ]
    
    # Concatenate all transcriptions
    full_text = " ".join([c["transcription"] for c in processed_chunks])
    
    return {
        "session_id": session_id,
        "total_chunks": len(processed_chunks),
        "full_transcript": full_text,
        "word_count": len(full_text.split())
    }


@router.post("/process/{session_id}")
async def trigger_transcription(
    session_id: str,
    background_tasks: BackgroundTasks,
    chunk_index: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Manually trigger transcription processing.
    
    If chunk_index provided: process that specific chunk.
    Otherwise: process all pending chunks for the session.
    """
    media_session = db.query(MediaSession).filter(
        MediaSession.session_id == session_id
    ).first()
    
    if not media_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    chunks = media_session.audio_chunks or []
    
    if chunk_index is not None:
        # Process specific chunk
        chunk = next((c for c in chunks if c.get("chunk_index") == chunk_index), None)
        
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        # Trigger in background
        background_tasks.add_task(
            process_audio_chunk_transcription,
            db=db,
            session_id=session_id,
            chunk_index=chunk_index,
            file_path=chunk["file_path"],
            language="en"
        )
        
        return {
            "message": f"Transcription triggered for chunk {chunk_index}",
            "chunk_index": chunk_index
        }
    else:
        # Process all pending chunks
        pending_chunks = [c for c in chunks if not c.get("processed", False)]
        
        for chunk in pending_chunks:
            background_tasks.add_task(
                process_audio_chunk_transcription,
                db=db,
                session_id=session_id,
                chunk_index=chunk["chunk_index"],
                file_path=chunk["file_path"],
                language="en"
            )
        
        return {
            "message": f"Transcription triggered for {len(pending_chunks)} chunks",
            "pending_chunks": len(pending_chunks)
        }


@router.post("/process-all")
async def process_all_pending(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Process ALL pending transcriptions across all sessions.
    
    Useful for catching up after system restart.
    """
    background_tasks.add_task(process_pending_transcriptions, db=db)
    
    return {
        "message": "Processing all pending transcriptions in background"
    }
