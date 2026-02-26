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
from src.services.aiservices import AudioProcessor, EmotionDetector,unload_whisper,unload_emotion,LLMService,load_whisper
from starlette.websockets import WebSocketDisconnect, WebSocketState,WebSocket

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
                data = await websocket.receive_json() # Let disconnects propagate to outer block
                print(f"📩 Received: {type(data)} - Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                
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

                        # # Store audio chunk
                        # try:
                        #     new_chunk = LiveChunksInput(
                        #         session_id=session_id,
                        #         audio_chunk=audio_bytes,
                        #         video_chunk=None,
                        #     )
                        #     db.add(new_chunk)
                        #     db.flush()
                        #     db.commit()
                        #     db.refresh(new_chunk)
                        #     chunk_count += 1
                        #     print(f"✅ Audio chunk #{chunk_count} STORED with ID={new_chunk.id} ({len(audio_bytes)} bytes)")
                            
                        # except Exception as e:
                        #     db.rollback()
                        #     print(f"❌ Database Error storing audio: {type(e).__name__}: {e}")
                        #     print(f"❌ Traceback:\n{traceback.format_exc()}")
                        #     continue

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
                            
                            new_chunk = LiveChunksInput(
                                session_id=session_id,
                                audio_chunk=None,
                                video_chunk=video_bytes
                            )
                            db.add(new_chunk)
                            db.flush()
                            db.commit()
                            chunk_count += 1
                            
                            # ⚡ LIVE ANALYSIS & STORAGE
                            emotion_detector = EmotionDetector() 
                            analysis_result = emotion_detector.analyze(video_bytes)
                            
                            # Store result immediately to avoid post-processing overhead
                            new_analysis = EmotionAnalysis(
                                session_id=session_id,
                                emotion_label=analysis_result['label'],
                                emotion_score=str(analysis_result['score'])
                            )
                            db.add(new_analysis)
                            db.commit()

                            from starlette.websockets import WebSocketState as WSState
                            if websocket.client_state == WSState.CONNECTED:
                                await websocket.send_json({
                                    "type": "live_emotion_analysis",
                                    "data": analysis_result,
                                    "chunk_number": chunk_count
                                })
                        except Exception as e:
                            db.rollback()
                            print(f"❌ Video analysis/storage error: {e}")

                    # ----- SESSION COMPLETE -----
                    # ----- SESSION COMPLETE -----
                    elif msg_type == "session_complete" or msg_type == "end_interview":
                        print(f"🛑 Session Complete received. Total chunks: {chunk_count}")
                        
                        # 1. ⏳ CRITICAL FIX: Flush any remaining audio in the buffer before unloading!
                        try:
                            final_transcription = await processor.flush()
                            if final_transcription and len(final_transcription.strip()) > 0:
                                last_question_id = data.get("question_number", None)
                                new_transcript = Transcript(
                                    session_id=session_id,
                                    user_response=final_transcription,
                                    is_ai_response=False,
                                    question_id=last_question_id
                                )
                                db.add(new_transcript)
                                db.commit()
                                print(f"✅ Final Flushed Transcript STORED: {final_transcription[:80]}...")
                                
                                # Send the final transcript back to the frontend so the UI updates
                                await websocket.send_json({
                                    "type": "transcription",
                                    "data": final_transcription,
                                    "chunk_number": chunk_count + 1
                                })
                        except Exception as e:
                            db.rollback()
                            print(f"❌ Final flush error: {e}")

                        # 2. Mark session complete
                        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
                        if session:
                            session.status = SessionStatus.COMPLETED
                            db.commit()

                        # 3. 🏁 CLEANUP: Now it is safe to unload models
                        unload_whisper()
                        unload_emotion()
                        
                        return {"message": "Session complete", "session_id": session_id}
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
            # 🧹 CRITICAL FIX: Guarantee models are unloaded no matter how the socket closes
            print("🧹 WebSocket closed. Executing final memory cleanup...")
            unload_whisper()
            unload_emotion()
            
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
    

    @staticmethod
    async def analyse_session(token: HTTPAuthorizationCredentials, db: Session, session_id: int):
        # 1. Verify User and Fetch Session
        user_id = get_current_user(token)
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found or unauthorized")

        # 1. Force release of STT memory
        unload_whisper()
        unload_emotion()
        
        llmservice = LLMService()
        # CRITICAL: Initialize the service's internal model before use
        llmservice.install_model("llm") 

        try:
            # 2. Analysis Loop
            unique_qids = {t.question_id for t in session.transcripts if t.question_id is not None}
            for qid in unique_qids:
                question = db.query(Questions).filter(Questions.id == qid).first()
                transcript = db.query(Transcript).filter(
                    Transcript.question_id == qid, 
                    Transcript.session_id == session_id
                ).first()
                
                if question and transcript:
                    cv_content = session.cv.cv_text if session.cv else "No CV provided"
                    
                    eval_result = await llmservice.evaluate_candidate_response(
                        q_id=qid,
                        question=question.question_text,
                        recommended_answer=question.recommended_answer or "No ideal answer provided",
                        candidate_response=transcript.user_response,
                        cv_text=cv_content
                    )
                    
                    qna_result = Qna_result(
                        session_id=session_id,
                        question_id=qid,
                        score=eval_result.get('score', 0),
                        feedback=eval_result.get('feedback', ''),
                        strength=", ".join(eval_result.get('strengths', [])),
                        weakness=", ".join(eval_result.get('improvements', []))
                    )
                    db.add(qna_result)

            # 4. Overall Emotion Result (Fetched from DB records saved during live session)
            emotion_records = db.query(EmotionAnalysis).filter(EmotionAnalysis.session_id == session_id).all()
            
            if emotion_records:
                # Reconstruct 'results' list from DB records
                results = [{"label": r.emotion_label, "score": float(r.emotion_score)} for r in emotion_records]
                overall_emotion = max(results, key=lambda x: x['score'])
                
                emo_eval = llmservice.evaluate_emotion(
                    emotion_label=[overall_emotion['label']], 
                    confidence_score=[overall_emotion['score']]
                )
                
                perception_text = emo_eval.get('perception', f"Overall emotion: {overall_emotion['label']}")
                recs = emo_eval.get('recommendations', [])
                recommendation_str = ", ".join(recs) if isinstance(recs, list) else str(recs)
                
                emotion_result = Emotion_result(
                    session_id=session_id,
                    perception=perception_text,
                    recommendation=recommendation_str,
                    confidence=str(overall_emotion['score'])
                )
                db.add(emotion_result)

            # 5. Final Commit and Unload
            db.commit()
            
            
            return {"status": "success", "message": "Analysis completed and saved"}

        except Exception as e:
            db.rollback()
            print(f"❌ Analysis failed: {e}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")