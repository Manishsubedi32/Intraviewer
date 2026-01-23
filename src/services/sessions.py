import base64
import json
from fastapi import HTTPException, Depends, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src import db
from src.models.models import LiveChunksInput, SessionStatus, InterviewSession, User, Transcript, Questions,AnalysisResult
from src.core.security import get_current_user
from src.services.aiservices import AudioProcessor
from starlette.websockets import WebSocketDisconnect, WebSocketState

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
        await websocket.accept()
        
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        
        if not session:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # it only owkrs when session is ongoing
        if session.status != SessionStatus.ONGOING:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        processor = AudioProcessor()
        
        try:
            while True:
                data = await websocket.receive_json() # yesma recieve_json is needed as text won't work
                print(type(data))        # <class 'dict'>
                print(data)
                # -------------------------------------------------------
                if "bytes" in data: # used to check if binary data is present
                    audio_bytes = data["bytes"]
                    
                    # 1. Store Raw Audio Chunk
                    new_chunk = LiveChunksInput(
                        session_id=session_id,
                        audio_chunk=audio_bytes, #this is base64 encoded string
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
                elif "text" in data: # as we know video is sent as text frame in base64 inside json
                    try:
                        payload = json.loads(data["text"])
                        msg_type = payload.get("type")
                        data_content = payload.get("data")

                        if msg_type == "video":
                            # Handle Video (sent as Base64 string inside JSON)
                            video_bytes = base64.b64decode(data_content)
                            new_chunk = LiveChunksInput(
                                session_id=session_id,
                                audio_chunk=None,
                                video_chunk=video_bytes
                            )
                            db.add(new_chunk)
                            db.commit()
                        
                        elif msg_type == "end_interview":
                            # Trigger your LLM analysis logic here
                            session.status = SessionStatus.COMPLETED
                            db.commit()

                            await websocket.send_json({"type": "status", "data": "Interview Completed"})
                            break

                    except json.JSONDecodeError:
                        print("Received invalid JSON text")

        except WebSocketDisconnect:
            print(f"Client disconnected from session {session_id}")
            # No need to close here, it's already disconnected
            
        except Exception as e:
            print(f"WebSocket Error: {e}")
            # Only close if still connected
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=1011) # Internal Error
                
        finally:
            # FIX: Check state before closing in finally block
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close()
                except RuntimeError:
                    # Ignore if it was already closed concurrently
                    pass
    
    @staticmethod
    async def fetch_session_analysis(token: HTTPAuthorizationCredentials, db: Session, session_id: int):
        user_id = get_current_user(token)
    
   
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id, 
            InterviewSession.user_id == user_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        
        # hamle specific quesiton lai specific analysis garexainam
        analysis = db.query(AnalysisResult).filter(
            AnalysisResult.session_id == session_id
        ).first()

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found for this session")

        return {
            "analysis_text": analysis.analysis_text,
            "score": analysis.score
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
        ).order_by(Transcript.created_at).all()

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
    
    @staticmethod
    async def delete_session(token: HTTPAuthorizationCredentials, db: Session, session_id: int):
        user_id = get_current_user(token)
        user = db.query(User).filter(User.id == user_id).first()
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Only admin can delete sessions")
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id,
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        db.delete(session)
        db.commit()
        
        return {"message": "Session deleted successfully"}