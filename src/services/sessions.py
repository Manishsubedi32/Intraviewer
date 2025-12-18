from fastapi import HTTPException , Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.models.models import SessionStatus, InterviewSession, User,Transcript # sqlalchemy models
from src.schemas.session import SessionBase #pydantic model
from src.core.security import get_current_user, auth_scheme
from src.core.security import get_password_hash
from aiservices import AudioProcessor  # hypothetical module for audio processing , we can get it from collab
class SessionService:
    @staticmethod
    async def create_session(token: HTTPAuthorizationCredentials, db: Session):
        user_id = get_current_user(token)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        new_session = InterviewSession(
            user_id=user_id,
            status=SessionStatus.ONGOING
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return {"message": "Session created successfully", "session_id": new_session.id}
    
    @staticmethod
    async def handle_session_websocket(websocket, session_id: int,db: Session):
        await websocket.accept()
        try:
            while True:
                # we are recieving our audio chunks here
                audio_chunks = await websocket.receive_bytes()
          
                #process the audio chunks and generate response
                transcription = await AudioProcessor.process_audio(audio_chunks)


                if transcription and len(transcription.strip()) > 0:
                    new_transcript = Transcript(
                        session_id=session_id, # Now this works with the fixed model
                        user_response=transcription,
                        is_ai_response=False
                    )
                    db.add(new_transcript)
                    db.commit()
                    
                    
                    await websocket.send_text(f"Transcription: {transcription}")
            
        except Exception as e:
                print(f"Error: {e}")
        finally:
                await websocket.close()