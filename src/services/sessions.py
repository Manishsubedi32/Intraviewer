import base64
import json
from fastapi import HTTPException, Depends, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src import db
from src.models.models import LiveChunksInput, SessionStatus, InterviewSession, User, Transcript, Questions
from src.core.security import get_current_user
from src.services.aiservices import AudioProcessor

class SessionService:
    @staticmethod
    async def create_session(token: HTTPAuthorizationCredentials, db: Session, cv_id: int, prompt_id: int):
        user_id = get_current_user(token)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        new_session = InterviewSession(
            user_id=user_id,
            cv_id=cv_id,
            prompt_id=prompt_id,
            status=SessionStatus.ONGOING
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return {"message": "Session created successfully", "session_id": new_session.id}

    @staticmethod
    async def complete_session(token: HTTPAuthorizationCredentials, db: Session, session_id: int):
        user_id = get_current_user(token)
        
        # Get the session and verify ownership
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or you don't have permission"
            )
        
        # Update session status to completed
        session.status = SessionStatus.COMPLETED
        db.commit()
        db.refresh(session)
        
        return {
            "message": "Session completed successfully",
            "session_id": session.id,
            "status": session.status.value
        }
    
    @staticmethod
    async def handle_session_websocket(websocket: WebSocket, session_id: int, db: Session):
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        
        if not session:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # it only owkrs when session is ongoing
        if session.status != SessionStatus.ONGOING:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()
        processor = AudioProcessor()
        
        try: 
            while True:
                message = await websocket.receive()
    
                # -------------------------------------------------------
                if "bytes" in message: # used to check if binary data is present
                    audio_bytes = message["bytes"]
                    
                    # 1. Store Raw Audio Chunk
                    new_chunk = LiveChunksInput(
                        session_id=session_id,
                        audio_chunk=audio_bytes, # Storing raw bytes is more efficient than Base64
                        video_chunk=None
                    )
                    db.add(new_chunk)
                    db.commit()

                    # 2. Process Audio
                    transcription = await processor.process_audio(audio_bytes)
                    
                    if transcription and len(transcription.strip()) > 0:
                        new_transcript = Transcript(
                            session_id=session_id,
                            user_response=transcription,
                            is_ai_response=False
                        )
                        db.add(new_transcript)
                        db.commit()
                        
                        await websocket.send_text(f"Transcription: {transcription}")

                # -------------------------------------------------------
                # CASE 2: TEXT FRAME -> JSON (Video, Commands, Config)
                # -------------------------------------------------------
                elif "text" in message: # as we know video is sent as text frame in base64 inside json
                    try:
                        payload = json.loads(message["text"])
                        msg_type = payload.get("type")
                        data_content = payload.get("data")

                        if msg_type == "video":
                            # Handle Video (sent as Base64 string inside JSON)
                            new_chunk = LiveChunksInput(
                                session_id=session_id,
                                audio_chunk=None,
                                video_chunk=data_content
                            )
                            db.add(new_chunk)
                            db.commit()
                        
                        elif msg_type == "end_interview":
                            # Trigger your LLM analysis logic here
                            pass

                    except json.JSONDecodeError:
                        print("Received invalid JSON text")

        except Exception as e:
                print(f"Error: {e}")
        finally:
                await websocket.close()
    
    @staticmethod
    async def fetch_session_analysis(token: HTTPAuthorizationCredentials, db: Session, session_id: int):

        user_id = get_current_user(token)
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        return {
            "session_id": session.id,
            "status": session.status,
            "final_score": session.final_score,
            "analysis_text": session.analysis,
            "created_at": session.start_time
        }

    @staticmethod
    async def fetch_session_transcript(token: HTTPAuthorizationCredentials, db: Session, session_id:int):
        user_id = get_current_user(token)
    
   
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id, 
            InterviewSession.user_id == user_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        
        # hamle specific quesiton lai specific transcript garexainam
        transcripts = db.query(Transcript).filter(
            Transcript.session_id == session_id
        ).order_by(Transcript.timestamp).all()

        return {
            "transcripts": [t.user_response for t in transcripts]
        }
    
    @staticmethod
    async def fetch_session_questions(token: HTTPAuthorizationCredentials, db: Session, session_id: int):
        user_id = get_current_user(token)
        
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        questions = db.query(Questions).filter(
            Questions.session_id == session_id
        ).order_by(Questions.order).all()
        
        return {
            "questions": [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "difficulty_level": q.difficulty_level,
                    "topic": q.topic,
                    "created_at": q.created_at
                } for q in questions
            ]
        }
    
    #session termination
    @staticmethod
    async def terminate_session(token: HTTPAuthorizationCredentials, db: Session, session_id: int):
        user_id = get_current_user(token)
        
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session.status = SessionStatus.TERMINATED
        db.commit()
        
        return {"message": "Session terminated successfully"}