from fastapi import HTTPException , Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.models.models import Questions, User, InterviewSession, Cv, TextPrompts # sqlalchemy models
from src.schemas.auth import QuestionBase #pydantic model
from src.core.security import get_current_user, auth_scheme
from src.core.security import get_password_hash
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
        new_question = Questions( # we are converting pydantic model to sqlalchemy model
            **question.model_dump()
        )
        db.add(new_question)
        db.commit()
        db.refresh(new_question)
        return {"message": "Question added successfully"}

    @staticmethod
    async def generate_and_save_questions(
        db: Session, 
        session_id: int
    ):
        """
        Generates questions using LLM by fetching the Session's CV and Prompt from the DB.
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

        # 3. Fetch Linked Job Description (TextPrompt)
        if not session.prompt_id:
             raise HTTPException(status_code=400, detail="Session does not have a Job Description/Prompt attached")

        prompt_record = db.query(TextPrompts).filter(TextPrompts.id == session.prompt_id).first()
        if not prompt_record:
             raise HTTPException(status_code=404, detail="Associated Prompt record not found")
        
        # UPDATED: Combine Topic Name and Prompt Text for better AI context
        job_context = f"INTERVIEW TOPIC: {prompt_record.name}\n\nJOB DESCRIPTION: {prompt_record.prompt_text}"

        # 4. Call AI Service
        llm_service = LLMService()
        print(f"Generating questions for Session {session_id}...")
        
        # Pass the combined context instead of just the prompt text
        questions_list = await llm_service.generate_interview_questions(cv_text, job_context)

        if not questions_list:
            raise HTTPException(status_code=500, detail="AI failed to generate questions")

        # 5. Save questions to Database
        saved_questions = []
        for i, q_text in enumerate(questions_list):
            new_question = Questions(
                session_id=session_id,
                question_text=q_text,
                order=i+1 # Store the order 1, 2, 3...
            )
            db.add(new_question)
            saved_questions.append(new_question)
        
        db.commit()
        
        for q in saved_questions:
            db.refresh(q)
            
        return saved_questions

    @staticmethod
    async def get_questions_by_session(db: Session, session_id: int):
        return db.query(Questions).filter(Questions.session_id == session_id).all()