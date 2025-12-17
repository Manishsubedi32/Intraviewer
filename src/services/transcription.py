"""
Faster-Whisper Speech-to-Text Transcription Service

Processes saved audio chunks and generates timestamped transcripts.
Uses faster-whisper for efficient CPU-based transcription.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import asyncio

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    Manages faster-whisper model and provides transcription functionality.
    
    Features:
    - Lazy model loading
    - Thread-pool execution (non-blocking)
    - Timestamped segments
    - Language detection
    - Memory-efficient processing
    """
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        num_workers: int = 1
    ):
        """
        Initialize transcription service.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v2)
            device: Device to run on (cpu, cuda)
            compute_type: Computation precision (int8, float16, float32)
            num_workers: Number of background worker threads
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model: Optional[WhisperModel] = None
        self.executor = ThreadPoolExecutor(max_workers=num_workers)
        
        logger.info(
            f"TranscriptionService initialized: "
            f"model={model_size}, device={device}, compute_type={compute_type}"
        )
    
    def load_model(self):
        """
        Load the faster-whisper model.
        Call this at application startup to avoid cold-start delays.
        """
        if self.model is not None:
            logger.info("Model already loaded")
            return
        
        start_time = time.time()
        logger.info(f"Loading faster-whisper model: {self.model_size}")
        
        try:
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root="./models",  # Cache models locally
                cpu_threads=4,  # Optimize CPU usage
            )
            
            load_duration = time.time() - start_time
            logger.info(f"✅ Model loaded successfully in {load_duration:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise
    
    def _transcribe_sync(
        self,
        audio_path: str,
        session_id: str,
        chunk_index: int,
        language: Optional[str] = None
    ) -> Dict:
        """
        Synchronous transcription function (runs in thread pool).
        
        Args:
            audio_path: Path to audio file
            session_id: Session identifier
            chunk_index: Chunk sequence number
            language: Language code (None for auto-detect)
        
        Returns:
            Structured transcript dictionary
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        start_time = time.time()
        logger.info(
            f"🎤 Transcribing: session={session_id}, "
            f"chunk={chunk_index}, file={audio_file.name}"
        )
        
        try:
            # Run transcription
            segments, info = self.model.transcribe(
                str(audio_path),
                language=language,
                beam_size=5,
                vad_filter=True,  # Voice Activity Detection
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    threshold=0.5
                ),
                word_timestamps=False,  # Set True for word-level timing
            )
            
            # Convert segments to list (segments is a generator)
            transcript_segments = []
            for segment in segments:
                transcript_segments.append({
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip(),
                    "confidence": round(segment.avg_logprob, 3) if hasattr(segment, 'avg_logprob') else None
                })
            
            duration = time.time() - start_time
            
            # Build result
            result = {
                "session_id": session_id,
                "chunk_index": chunk_index,
                "language": info.language if hasattr(info, 'language') else language,
                "language_probability": round(info.language_probability, 3) if hasattr(info, 'language_probability') else None,
                "duration_seconds": info.duration if hasattr(info, 'duration') else None,
                "segments": transcript_segments,
                "full_text": " ".join([s["text"] for s in transcript_segments]),
                "processing_time": round(duration, 2)
            }
            
            logger.info(
                f"✅ Transcription complete: session={session_id}, "
                f"chunk={chunk_index}, segments={len(transcript_segments)}, "
                f"took {duration:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"❌ Transcription failed: session={session_id}, "
                f"chunk={chunk_index}, error={str(e)}"
            )
            raise
    
    async def transcribe(
        self,
        audio_path: str,
        session_id: str,
        chunk_index: int,
        language: Optional[str] = None
    ) -> Dict:
        """
        Async transcription function (non-blocking).
        
        Runs transcription in thread pool to avoid blocking event loop.
        
        Args:
            audio_path: Path to audio file
            session_id: Session identifier
            chunk_index: Chunk sequence number
            language: Language code (None for auto-detect)
        
        Returns:
            Structured transcript dictionary
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self._transcribe_sync,
            audio_path,
            session_id,
            chunk_index,
            language
        )
        return result
    
    def shutdown(self):
        """
        Clean shutdown of transcription service.
        Call this on application shutdown.
        """
        logger.info("Shutting down TranscriptionService")
        self.executor.shutdown(wait=True)
        self.model = None


# Global service instance
_transcription_service: Optional[TranscriptionService] = None


def get_transcription_service() -> TranscriptionService:
    """
    Get or create the global transcription service instance.
    
    Returns:
        TranscriptionService instance
    """
    global _transcription_service
    
    if _transcription_service is None:
        _transcription_service = TranscriptionService(
            model_size="base",  # Options: tiny, base, small, medium, large-v2
            device="cpu",
            compute_type="int8",  # Optimized for CPU
            num_workers=2  # Parallel processing
        )
    
    return _transcription_service


async def transcribe_audio_chunk(
    audio_path: str,
    session_id: str,
    chunk_index: int,
    language: Optional[str] = None
) -> Dict:
    """
    High-level transcription function for easy integration.
    
    Usage:
        result = await transcribe_audio_chunk(
            audio_path="/path/to/audio.webm",
            session_id="uuid-here",
            chunk_index=5,
            language="en"  # Optional
        )
    
    Args:
        audio_path: Path to audio file
        session_id: Session identifier
        chunk_index: Chunk sequence number
        language: Language code (None for auto-detect)
    
    Returns:
        Transcript dictionary with segments and metadata
    """
    service = get_transcription_service()
    return await service.transcribe(
        audio_path=audio_path,
        session_id=session_id,
        chunk_index=chunk_index,
        language=language
    )
