"""
Media Streaming WebSocket Endpoint

Handles real-time audio and video frame streaming from browser clients.
- Accepts WebSocket connections
- Receives JSON metadata and binary blobs
- Manages multiple concurrent sessions
- Stores data to disk and metadata to database
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import json
import os
import asyncio
from pathlib import Path
from typing import Dict, Set
import uuid

from src.db.database import get_db
from src.models.models import MediaSession, AudioChunk, VideoFrame


router = APIRouter(tags=["media-stream"])

# In-memory session management
active_sessions: Dict[str, WebSocket] = {}
session_buffers: Dict[str, dict] = {}


# Storage configuration
STORAGE_BASE_PATH = os.getenv("MEDIA_STORAGE_PATH", "./media_storage")
Path(STORAGE_BASE_PATH).mkdir(parents=True, exist_ok=True)


# ============================================
# Session Management
# ============================================

def create_session_storage(session_id: str) -> str:
    """Create storage directory for a session"""
    session_path = Path(STORAGE_BASE_PATH) / session_id
    session_path.mkdir(parents=True, exist_ok=True)
    (session_path / "audio").mkdir(exist_ok=True)
    (session_path / "frames").mkdir(exist_ok=True)
    return str(session_path)


def cleanup_inactive_sessions(db: Session):
    """Clean up sessions inactive for > 5 minutes"""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    
    inactive = db.query(MediaSession).filter(
        MediaSession.status == "active",
        MediaSession.last_activity < cutoff
    ).all()
    
    for session in inactive:
        session.status = "abandoned"
        db.commit()
        
        # Remove from active tracking
        if session.session_id in active_sessions:
            del active_sessions[session.session_id]
        if session.session_id in session_buffers:
            del session_buffers[session.session_id]


# ============================================
# WebSocket Message Handlers
# ============================================

async def handle_session_init(data: dict, websocket: WebSocket, db: Session):
    """Handle session initialization message"""
    session_id = data.get("session_id")
    user_id = data.get("user_id", 1)  # TODO: Get from auth
    interview_session_id = data.get("interview_session_id")
    
    # Check if session already exists
    media_session = db.query(MediaSession).filter(
        MediaSession.session_id == session_id
    ).first()
    
    if not media_session:
        # Create new session
        storage_path = create_session_storage(session_id)
        
        media_session = MediaSession(
            session_id=session_id,
            user_id=user_id,
            interview_session_id=interview_session_id,
            storage_path=storage_path,
            status="active"
        )
        db.add(media_session)
        db.commit()
        db.refresh(media_session)
    
    # Track active connection
    active_sessions[session_id] = websocket
    session_buffers[session_id] = {
        "db_session_id": media_session.id,
        "chunks_received": 0,
        "frames_received": 0
    }
    
    # Send acknowledgment
    await websocket.send_json({
        "type": "session_init_ack",
        "session_id": session_id,
        "status": "ready"
    })


async def handle_audio_metadata(data: dict, db: Session):
    """Handle audio chunk metadata before receiving blob"""
    session_id = data.get("session_id")
    chunk_index = data.get("chunk_index")
    start_timestamp = data.get("start_timestamp")
    end_timestamp = data.get("end_timestamp")
    duration_ms = data.get("duration_ms")
    
    if session_id not in session_buffers:
        return
    
    buffer = session_buffers[session_id]
    
    # Store metadata in buffer, waiting for blob
    buffer[f"audio_chunk_{chunk_index}"] = {
        "chunk_index": chunk_index,
        "start_timestamp": datetime.fromisoformat(start_timestamp.replace('Z', '+00:00')),
        "end_timestamp": datetime.fromisoformat(end_timestamp.replace('Z', '+00:00')) if end_timestamp else None,
        "duration_ms": duration_ms,
        "metadata_received": True,
        "blob_received": False
    }


async def handle_audio_blob(session_id: str, chunk_index: int, blob_data: bytes, db: Session):
    """Handle audio chunk blob data"""
    if session_id not in session_buffers:
        return
    
    buffer = session_buffers[session_id]
    chunk_key = f"audio_chunk_{chunk_index}"
    
    if chunk_key not in buffer:
        # Metadata not received yet, store blob temporarily
        buffer[chunk_key] = {
            "chunk_index": chunk_index,
            "blob_received": True,
            "blob_data": blob_data,
            "metadata_received": False
        }
        return
    
    chunk_meta = buffer[chunk_key]
    
    # Save blob to disk
    media_session = db.query(MediaSession).filter(
        MediaSession.id == buffer["db_session_id"]
    ).first()
    
    if not media_session:
        return
    
    file_path = f"{media_session.storage_path}/audio/chunk_{chunk_index}.webm"
    
    with open(file_path, "wb") as f:
        f.write(blob_data)
    
    # Save metadata to database
    audio_chunk = AudioChunk(
        media_session_id=media_session.id,
        chunk_index=chunk_index,
        file_path=file_path,
        file_size=len(blob_data),
        mime_type="audio/webm",
        start_timestamp=chunk_meta.get("start_timestamp"),
        end_timestamp=chunk_meta.get("end_timestamp"),
        duration_ms=chunk_meta.get("duration_ms")
    )
    
    db.add(audio_chunk)
    media_session.total_chunks += 1
    media_session.last_activity = datetime.utcnow()
    db.commit()
    
    # Clear from buffer
    del buffer[chunk_key]
    buffer["chunks_received"] += 1
    
    print(f"✅ Audio chunk {chunk_index} saved for session {session_id}")


async def handle_frame_metadata(data: dict, db: Session):
    """Handle video frame metadata before receiving blob"""
    session_id = data.get("session_id")
    frame_index = data.get("frame_index")
    chunk_index = data.get("chunk_index")
    timestamp = data.get("timestamp")
    offset_ms = data.get("offset_ms")
    
    if session_id not in session_buffers:
        return
    
    buffer = session_buffers[session_id]
    
    # Store metadata in buffer
    buffer[f"frame_{frame_index}"] = {
        "frame_index": frame_index,
        "chunk_index": chunk_index,
        "timestamp": datetime.fromisoformat(timestamp.replace('Z', '+00:00')),
        "offset_ms": offset_ms,
        "metadata_received": True,
        "blob_received": False
    }


async def handle_frame_blob(session_id: str, frame_index: int, blob_data: bytes, db: Session):
    """Handle video frame blob data"""
    if session_id not in session_buffers:
        return
    
    buffer = session_buffers[session_id]
    frame_key = f"frame_{frame_index}"
    
    if frame_key not in buffer:
        # Metadata not received yet
        buffer[frame_key] = {
            "frame_index": frame_index,
            "blob_received": True,
            "blob_data": blob_data,
            "metadata_received": False
        }
        return
    
    frame_meta = buffer[frame_key]
    
    # Save blob to disk
    media_session = db.query(MediaSession).filter(
        MediaSession.id == buffer["db_session_id"]
    ).first()
    
    if not media_session:
        return
    
    file_path = f"{media_session.storage_path}/frames/frame_{frame_index}.jpg"
    
    with open(file_path, "wb") as f:
        f.write(blob_data)
    
    # Find associated audio chunk
    audio_chunk = db.query(AudioChunk).filter(
        AudioChunk.media_session_id == media_session.id,
        AudioChunk.chunk_index == frame_meta.get("chunk_index")
    ).first()
    
    # Save metadata to database
    video_frame = VideoFrame(
        media_session_id=media_session.id,
        audio_chunk_id=audio_chunk.id if audio_chunk else None,
        frame_index=frame_meta.get("frame_index"),
        chunk_index=frame_meta.get("chunk_index"),
        file_path=file_path,
        file_size=len(blob_data),
        mime_type="image/jpeg",
        timestamp=frame_meta.get("timestamp"),
        offset_ms=frame_meta.get("offset_ms")
    )
    
    db.add(video_frame)
    media_session.total_frames += 1
    media_session.last_activity = datetime.utcnow()
    db.commit()
    
    # Clear from buffer
    del buffer[frame_key]
    buffer["frames_received"] += 1
    
    print(f"✅ Frame {frame_index} saved for session {session_id}")


async def handle_session_complete(data: dict, db: Session):
    """Handle session completion"""
    session_id = data.get("session_id")
    
    media_session = db.query(MediaSession).filter(
        MediaSession.session_id == session_id
    ).first()
    
    if media_session:
        media_session.status = "completed"
        media_session.completed_at = datetime.utcnow()
        db.commit()
    
    # Cleanup
    if session_id in active_sessions:
        del active_sessions[session_id]
    if session_id in session_buffers:
        del session_buffers[session_id]
    
    print(f"✅ Session {session_id} completed")


# ============================================
# WebSocket Endpoint
# ============================================

@router.websocket("/ws/media-stream")
async def media_stream_websocket(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for real-time media streaming
    
    Message formats:
    
    JSON Messages:
    - session_init: Initialize session
    - audio_metadata: Audio chunk metadata
    - frame_metadata: Frame metadata
    - session_complete: End session
    
    Binary Messages:
    - First 36 bytes: session_id (UUID string)
    - Next 1 byte: type ('a' for audio, 'f' for frame)
    - Next 4 bytes: index (chunk_index or frame_index)
    - Remaining: blob data
    """
    
    await websocket.accept()
    session_id = None
    
    try:
        while True:
            # Receive message (text or binary)
            message = await websocket.receive()
            
            if "text" in message:
                # JSON metadata message
                data = json.loads(message["text"])
                msg_type = data.get("type")
                
                if msg_type == "session_init":
                    await handle_session_init(data, websocket, db)
                    session_id = data.get("session_id")
                
                elif msg_type == "audio_metadata":
                    await handle_audio_metadata(data, db)
                
                elif msg_type == "frame_metadata":
                    await handle_frame_metadata(data, db)
                
                elif msg_type == "session_complete":
                    await handle_session_complete(data, db)
                    await websocket.send_json({"type": "complete_ack"})
                
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
            
            elif "bytes" in message:
                # Binary blob message
                blob_data = message["bytes"]
                
                # Parse header: [session_id(36)][type(1)][index(4)][data...]
                if len(blob_data) < 41:
                    continue
                
                session_id_bytes = blob_data[:36].decode('utf-8')
                blob_type = chr(blob_data[36])
                index = int.from_bytes(blob_data[37:41], 'big')
                data = blob_data[41:]
                
                if blob_type == 'a':
                    # Audio chunk
                    await handle_audio_blob(session_id_bytes, index, data, db)
                    await websocket.send_json({
                        "type": "audio_ack",
                        "chunk_index": index
                    })
                
                elif blob_type == 'f':
                    # Video frame
                    await handle_frame_blob(session_id_bytes, index, data, db)
                    await websocket.send_json({
                        "type": "frame_ack",
                        "frame_index": index
                    })
    
    except WebSocketDisconnect:
        print(f"Client disconnected: {session_id}")
        if session_id:
            if session_id in active_sessions:
                del active_sessions[session_id]
            # Don't delete buffer - allow reconnect
    
    except Exception as e:
        print(f"Error in WebSocket: {e}")
        await websocket.close(code=1011, reason=str(e))


# ============================================
# HTTP Endpoints for Session Management
# ============================================

@router.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str, db: Session = Depends(get_db)):
    """Get status of a media session"""
    media_session = db.query(MediaSession).filter(
        MediaSession.session_id == session_id
    ).first()
    
    if not media_session:
        return {"error": "Session not found"}
    
    return {
        "session_id": session_id,
        "status": media_session.status,
        "total_chunks": media_session.total_chunks,
        "total_frames": media_session.total_frames,
        "started_at": media_session.started_at,
        "last_activity": media_session.last_activity,
        "is_connected": session_id in active_sessions
    }
