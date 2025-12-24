import base64
from fastapi import HTTPException , Depends, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.models.models import LiveChunksInput, SessionStatus, InterviewSession, User,Transcript # sqlalchemy models
from src.schemas.session import SessionBase #pydantic model
from src.core.security import get_current_user, auth_scheme
from src.core.security import get_password_hash
from src.services.aiservices import AudioProcessor  # hypothetical module for audio processing , we can get it from collab
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
    async def handle_session_websocket(websocket: WebSocket, session_id: int,db: Session):
        await websocket.accept()
        processor = AudioProcessor() # instance of audio processing
        try: 
            while True:
                message = await websocket.receive_json()
                
                msg_type = message.get("type") # uta bata pathauni kun type
                data_b64 = message.get("data")# actual data

                if not data_b64:
                    continue

                if msg_type == "audio":
                    # 1. Store audio chunk
                    new_chunk = LiveChunksInput(
                        session_id=session_id,
                        audio_chunk=data_b64,# this is binary data in base64 format got audio, this is done to transfer audio in json format cause json cant handle binary data directly
                        video_chunk=None
                    )
                    db.add(new_chunk)
                    db.commit()

                    # 2. Process audio (decode base64 first)
                    audio_bytes = base64.b64decode(data_b64) # by decoding we get original audio bytes from json transferred data
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

                elif msg_type == "video":
                    # 1. Store video chunk
                    new_chunk = LiveChunksInput(
                        session_id=session_id,
                        audio_chunk=None,
                        video_chunk=data_b64
                    )
                    db.add(new_chunk)
                    db.commit()
                    
                    # Future: Add emotion detection logic here
            
        except Exception as e:
                print(f"Error: {e}")
        finally:
                await websocket.close()