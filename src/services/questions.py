from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.models.models import Questions, User, InterviewSession, Cv, TextPrompts
from src.routers import questions
from src.schemas.auth import QuestionBase
from src.core.security import get_current_user, auth_scheme
from src.services.aiservices import LLMService


class QuestionsService:
    @staticmethod
    async def allQuestions(token: HTTPAuthorizationCredentials, db: Session):
        user_id = get_current_user(token)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        questions = db.query(Questions).all()
        return questions

    @staticmethod
    async def addQuestion(token: HTTPAuthorizationCredentials, db: Session, question: QuestionBase):
        user_id = get_current_user(token)
        print(user_id)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.role != 'admin':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can add questions")
        new_question = Questions(
            **question.model_dump()
        )
        db.add(new_question)
        db.commit()
        db.refresh(new_question)
        return {"message": "Question added successfully"}

    @staticmethod
    async def generate_and_save_questions(db: Session, session_id: int):
        """
        Generates questions WITH recommended answers using LLM.
        Fetches Session's CV and Prompt from DB.
        """
        # 1. Fetch Session
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # 2. Fetch Linked CV
        if not session.cv_id:
            raise HTTPException(status_code=400, detail="Session does not have a CV attached")

        cv_record = db.query(Cv).filter(Cv.id == session.cv_id).first()
        if not cv_record:
            raise HTTPException(status_code=404, detail="Associated CV record not found")

        cv_text = cv_record.cv_text
        if not cv_text or len(cv_text.strip()) == 0:
            raise HTTPException(status_code=400, detail="CV text is empty. Please re-upload the CV.")

        print(f"📄 CV text loaded: {len(cv_text)} chars")

        # 3. Fetch Linked Job Description (TextPrompt)
        if not session.prompt_id:
            raise HTTPException(status_code=400, detail="Session does not have a Job Description/Prompt attached")

        prompt_record = db.query(TextPrompts).filter(TextPrompts.id == session.prompt_id).first()
        if not prompt_record:
            raise HTTPException(status_code=404, detail="Associated Prompt record not found")

        # Combine Topic Name and Prompt Text for better AI context
        job_context = f"INTERVIEW TOPIC: {prompt_record.name}\n\nJOB DESCRIPTION: {prompt_record.prompt_text}"
        print(f"💼 Job context loaded: {len(job_context)} chars")

        # 4. Call AI Service - now returns questions WITH recommended answers
        llm_service = LLMService()
        print(f"🤖 Generating questions with recommended answers for Session {session_id}...")

        questions_with_answers = await llm_service.generate_interview_questions(cv_text, job_context)

        if not questions_with_answers:
            raise HTTPException(status_code=500, detail="AI failed to generate questions")

        # 5. Save questions WITH recommended answers to Database
        saved_questions = []
        for i, q_data in enumerate(questions_with_answers):
            question_text = q_data.get("question", "")
            recommended_answer = q_data.get("recommended_answer", "")

            new_question = Questions(
                session_id=session_id,
                question_text=question_text,
                recommended_answer=recommended_answer,  # ✅ Save recommended answer
                order=i + 1
            )
            db.add(new_question)
            saved_questions.append({
                "question_text": question_text,
                "recommended_answer": recommended_answer,
                "order": i + 1
            })

        db.commit()

        print(f"✅ Saved {len(saved_questions)} questions with recommended answers")

        return saved_questions

    @staticmethod
    async def get_questions_by_session(db: Session, session_id: int): 
        """Get all questions for a session (without recommended answers)."""
        questions = db.query(Questions).filter(
            Questions.session_id == session_id
        ).order_by(Questions.order).all()
        
        # Return only the fields you want (excluding recommended_answer)
        return [
            {
                "id": q.id,
                "session_id": q.session_id,
                "question_text": q.question_text,
                "difficulty_level": q.difficulty_level.value if q.difficulty_level else None,
                "order": q.order,
                "created_at": q.created_at
            } for q in questions
        ]

    @staticmethod
    async def get_questions_with_answers(token: HTTPAuthorizationCredentials, db: Session, session_id: int): 
        """Get questions with their recommended answers for a session."""
        user_id = get_current_user(token)

        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found or access denied")

        questions = db.query(Questions).filter(
            Questions.session_id == session_id
        ).order_by(Questions.order).all()

        return {
            "session_id": session_id,
            "total_questions": len(questions),
            "questions": [
                {
                    "id": q.id,
                    "order": q.order,
                    "question_text": q.question_text,
                    "recommended_answer": q.recommended_answer,
                    "difficulty_level": q.difficulty_level.value if q.difficulty_level else None
                } for q in questions
            ]
        }