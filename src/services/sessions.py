import base64
import json
import asyncio
import traceback
from fastapi import HTTPException, Depends, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import text
from src.models.models import LiveChunksInput, SessionStatus, InterviewSession, User, Transcript, Questions , EmotionAnalysis , Qna_result,Emotion_result
from src.core.security import get_current_user
from src.services.aiservices import AudioProcessor, EmotionDetector,unload_whisper,unload_emotion,LLMService
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
        # emotion_detector = EmotionDetector() # ⚡ MOVED to end of session
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
                                video_chunk=None,
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
                            question_id = data.get("question_number", None)
                            transcription = await processor.process_audio(audio_bytes)
                            if transcription and len(transcription.strip()) > 0:
                                new_transcript = Transcript(
                                    session_id=session_id,
                                    user_response=transcription,
                                    is_ai_response=False,
                                    question_id=question_id
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
                                print(f"transcript sent = {transcription}")
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

                        # sending back live analysed frame to frontend
                        try:
                            emotion_detector = EmotionDetector() 
                            analysis_result = emotion_detector.analyze(video_bytes)
                            await websocket.send_json({
                                "type": "live_emotion_analysis",
                                "data": analysis_result,
                                "chunk_number": chunk_count
                            })
                        except Exception as e:
                            print(f"❌ Live emotion analysis error: {e}")
                            print(f"❌ Traceback:\n{traceback.format_exc()}")

                    # ----- SESSION COMPLETE -----
                    elif msg_type == "session_complete" or msg_type == "end_interview":
                        print(f"🛑 Session Complete received. Total chunks: {chunk_count}")
                        # Update session status to COMPLETED
                        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
                        print("unloading whisper",unload_whisper())
                        if session:
                            session.status = SessionStatus.COMPLETED
                            db.commit()
                            print(f"✅ Session {session_id} marked as COMPLETED")

                        # ------------------------------------------------------------------
                        # ⚡ POST-PROCESSING: ANALYZE VIDEO FRAMES NOW
                        # ------------------------------------------------------------------
                        try:
                            print("⏳ Starting Post-Session Emotion Analysis...")
                            
                            # Try to tell client we are starting, but ignore if they left
                            try:
                                await websocket.send_json({"type": "status", "data": "Processing video analysis..."})
                            except Exception:
                                print("⚠️ Client disconnected, continuing analysis in background...")

                            # 1. Load Detector 
                        
                            emotion_detector = EmotionDetector() 
                            
                            # 2. Fetch all video frames for this session
                            video_chunks = db.query(LiveChunksInput).filter(
                                LiveChunksInput.session_id == session_id,
                                LiveChunksInput.video_chunk != None
                            ).order_by(LiveChunksInput.id).all()
                            
                            print(f"   🎥 Found {len(video_chunks)} frames to analyze.")
                            
                            results = []
                            for i, chunk in enumerate(video_chunks):
                                if chunk.video_chunk:
                                    # Analyze individual frame
                                    analysis = emotion_detector.analyze(chunk.video_chunk)
                                    results.append(analysis)
                                    
                                    # Try to send progress, but don't crash if failed
                                    try:
                                        if i % 5 == 0:
                                            await websocket.send_json({
                                                "type": "status", 
                                                "data": f"Analyzed frame {i+1}/{len(video_chunks)}"
                                            })
                                    except Exception:
                                        pass # Client is gone, that's fine

                            # 3. Store Results to DB (CRITICAL STEP)
                            # You need to save 'results' into the 'InterviewSession' or 'AnalysisResult' table here!
                            # Currently your code just prints it and tries to send it.

                            for result in results:
                                emotion_analysis = EmotionAnalysis(
                                    session_id=session_id,
                                    emotion_label=result['label'],
                                    emotion_score=str(result['score'])
                                )
                                db.add(emotion_analysis)
                            
                            db.commit()
                            
                            
                            print(f"✅ Emotion Analysis Complete. Processed {len(results)} frames.")
                            unload_emotion()

                            # for sending single questionid and creating result for qna_result table by applying loop for each question and its corresponding transcript and emotion analysis result and then applying llm to generate feedback, strength and weakness and then storing in qna_result table
                            LLMService.install_model(instruction="llm")
                            evaluation = []
                            for qid in session.transcripts.question_id:
                                question = db.query(Questions).filter(Questions.id == qid).first()
                                transcript = db.query(Transcript).filter(Transcript.question_id == qid, Transcript.session_id == session_id).first()       
                                evaluation.append(LLMService.evaluate_candidate_response(
                                    q_id=qid,
                                    question=question.question_text,
                                    recommended_answer=question.recommended_answer,
                                    candidate_response=transcript.user_response,
                                    cv_text= session.cv.cv_text
                                ))
                                qna_result = Qna_result(
                                    session_id=session_id,
                                    question_id=qid,
                                    score=evaluation[-1]['score'],
                                    feedback=evaluation[-1]['feedback'],
                                    strength=evaluation[-1]['strength'],
                                    weakness=evaluation[-1]['weakness']
                                )
                                db.add(qna_result)
                            # now for emotion result for whole session we can take overall emotion analysis result and then generate perception, recommendation and confidence level using llm and then store in emotion_result table
                            overall_emotion = max(results, key=lambda x: x['score']) if results else None
                            if overall_emotion:
                                perception = f"Overall emotion detected: {overall_emotion['label']} with confidence {overall_emotion['score']:.2f}"
                                recommendation = LLMService.generate_emotion_recommendation(overall_emotion['label'])
                                confidence = f"{overall_emotion['score']:.2f}"
                                
                                emotion_result = Emotion_result(
                                    session_id=session_id,
                                    perception=perception,
                                    recommendation=recommendation,
                                    confidence=confidence
                                )
                                db.add(emotion_result)
                            
                            db.commit()
                            LLMService.install_model(instruction="unload")
                            # Final attempt to send
                            try:
                        # Only attempt to send if the connection is still open
                                from starlette.websockets import WebSocketState
                                if websocket.client_state == WebSocketState.CONNECTED:
                                    await websocket.send_json({
                                        "type": "analysis_complete",
                                        "data": "Analysis processed successfully"
                                    })
                            except Exception as e:
                                print(f"⚠️ Could not send analysis result via WebSocket (Client Disconnected): {e}")
                            

                        except Exception as e:
                            print(f"❌ Post-processing error: {e}")
                            traceback.print_exc()
                        # ------------------------------------------------------------------

                        # Mark session complete
                        try:
                            session.status = SessionStatus.COMPLETED
                            db.commit()
                            print(f"✅ Session COMPLETED")
                        except Exception as e:
                            db.rollback()
                            print(f"❌ Session update error: {e}")
                        
                        print(f"Analyzing result for qna response and emotion result and saving to db")
                            #qna needs

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

        emotionl_result = db.query(Emotion_result).filter(Emotion_result.session_id == session_id).first()
        qna_results = db.query(Qna_result).filter(Qna_result.session_id == session_id).all()

        if not emotionl_result or not qna_results:
            raise HTTPException(status_code=404, detail="Analysis not found for this session")

        return {
            "emotion_analysis": emotionl_result,
            "qna_results": qna_results
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
            "transcripts": [{"response": t.user_response, "question_id": t.question_id} for t in transcripts]
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