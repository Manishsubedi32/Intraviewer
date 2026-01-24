import base64
import json
import asyncio
import traceback
from fastapi import HTTPException, Depends, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import text
from src.models.models import LiveChunksInput, SessionStatus, InterviewSession, User, Transcript, Questions, AnalysisResult
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
        
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or you don't have permission"
            )
        
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
            print(f"❌ Session {session_id} not found")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        if session.status != SessionStatus.ONGOING:
            print(f"❌ Session {session_id} is not ONGOING (status: {session.status})")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        print(f"✅ Session {session_id} found and ONGOING")
        processor = AudioProcessor()
        chunk_count = 0
        
        try:
            while True:
                try:
                    data = await websocket.receive_json()
                    print(f"📩 Received: {type(data)} - Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                except Exception as e:
                    print(f"❌ JSON receive error: {e}")
                    continue

                # -------------------------------------------------------
                # Handle messages with "type" and "data" keys
                # This is the format your client is sending!
                # -------------------------------------------------------
                if "type" in data:
                    msg_type = data.get("type")
                    msg_data = data.get("data")
                    
                    print(f"📨 Message type: {msg_type}")

                    # ----- AUDIO DATA -----
                    if msg_type == "audio":
                        try:
                            audio_bytes = base64.b64decode(msg_data)
                            print(f"✅ Decoded audio: {len(audio_bytes)} bytes")
                        except Exception as e:
                            print(f"❌ Base64 Decode Error: {e}")
                            await websocket.send_json({"error": f"Base64 decode failed: {str(e)}"})
                            continue

                        # Store audio chunk
                        try:
                            new_chunk = LiveChunksInput(
                                session_id=session_id,
                                audio_chunk=audio_bytes,
                                video_chunk=None
                            )
                            db.add(new_chunk)
                            db.flush()
                            db.commit()
                            db.refresh(new_chunk)
                            chunk_count += 1
                            print(f"✅ Audio chunk #{chunk_count} STORED with ID={new_chunk.id} ({len(audio_bytes)} bytes)")
                            
                        except Exception as e:
                            db.rollback()
                            print(f"❌ Database Error storing audio: {type(e).__name__}: {e}")
                            print(f"❌ Traceback:\n{traceback.format_exc()}")
                            continue

                        # Process audio for transcription
                        try:
                            transcription = await processor.process_audio(audio_bytes)
                            if transcription and len(transcription.strip()) > 0:
                                new_transcript = Transcript(
                                    session_id=session_id,
                                    user_response=transcription,
                                    is_ai_response=False
                                )
                                db.add(new_transcript)
                                db.flush()
                                db.commit()
                                print(f"✅ Transcript STORED: {transcription[:80]}...")
                                
                                await websocket.send_json({
                                    "type": "transcription",
                                    "data": transcription,
                                    "chunk_number": chunk_count
                                })
                        except Exception as e:
                            db.rollback()
                            print(f"❌ Transcription error: {e}")

                    # ----- VIDEO DATA -----
                    elif msg_type == "video":
                        try:
                            video_bytes = base64.b64decode(msg_data)
                            print(f"✅ Decoded video: {len(video_bytes)} bytes")
                            
                            new_chunk = LiveChunksInput(
                                session_id=session_id,
                                audio_chunk=None,
                                video_chunk=video_bytes
                            )
                            db.add(new_chunk)
                            db.flush()
                            db.commit()
                            db.refresh(new_chunk)
                            chunk_count += 1
                            print(f"✅ Video chunk #{chunk_count} STORED with ID={new_chunk.id}")
                            
                        except Exception as e:
                            db.rollback()
                            print(f"❌ Video storage error: {e}")
                            print(f"❌ Traceback:\n{traceback.format_exc()}")

                    # ----- SESSION COMPLETE -----
                    elif msg_type == "session_complete" or msg_type == "end_interview":
                        print(f"🛑 Session Complete received. Total chunks: {chunk_count}")
                        
                        # Flush remaining audio
                        try:
                            final_transcript = await processor.flush()
                            if final_transcript and len(final_transcript.strip()) > 0:
                                new_transcript = Transcript(
                                    session_id=session_id,
                                    user_response=final_transcript,
                                    is_ai_response=False
                                )
                                db.add(new_transcript)
                                db.flush()
                                db.commit()
                                print(f"✅ Final transcript STORED")
                        except Exception as e:
                            db.rollback()
                            print(f"❌ Final flush error: {e}")

                        # Mark session complete
                        try:
                            session.status = SessionStatus.COMPLETED
                            db.commit()
                            print(f"✅ Session COMPLETED")
                        except Exception as e:
                            db.rollback()
                            print(f"❌ Session update error: {e}")

                        await websocket.send_json({
                            "type": "status",
                            "data": "Interview Completed",
                            "total_chunks": chunk_count
                        })
                        break

                    else:
                        print(f"⚠️ Unknown message type: {msg_type}")

                # -------------------------------------------------------
                # Legacy format: {"bytes": "..."} 
                # -------------------------------------------------------
                elif "bytes" in data:
                    try:
                        audio_bytes = base64.b64decode(data["bytes"])
                        print(f"✅ Decoded audio (legacy): {len(audio_bytes)} bytes")
                        
                        new_chunk = LiveChunksInput(
                            session_id=session_id,
                            audio_chunk=audio_bytes,
                            video_chunk=None
                        )
                        db.add(new_chunk)
                        db.flush()
                        db.commit()
                        db.refresh(new_chunk)
                        chunk_count += 1
                        print(f"✅ Audio chunk #{chunk_count} STORED (legacy)")
                        
                    except Exception as e:
                        db.rollback()
                        print(f"❌ Legacy audio error: {e}")

                else:
                    print(f"⚠️ Unknown message format: {list(data.keys())}")

        except WebSocketDisconnect:
            print(f"⚠️ Client disconnected from session {session_id}. Total chunks: {chunk_count}")
            
        except Exception as e:
            print(f"❌ Critical error: {type(e).__name__}: {e}")
            print(f"❌ Traceback:\n{traceback.format_exc()}")
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close(code=1011)
                except RuntimeError:
                    pass
                
        finally:
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close()
                except RuntimeError:
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