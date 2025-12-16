from sqlalchemy import Boolean, Column, ForeignKey, Integer, String,Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from sqlalchemy.sql.sqltypes import TIMESTAMP,Time  
from src.db.database import Base


from sqlalchemy.dialects.postgresql import JSONB



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, unique=True, nullable=False,index = True)
    firstname = Column(String, unique=False, nullable = False)
    lastname = Column(String, unique=False, nullable = False)
    email = Column(String, unique=True, nullable = False)
    password = Column(String, nullable = False)
    role = Column(String, nullable = False, server_default="user")
    is_active = Column(Boolean, server_default="True", nullable=False)
    created_at = Column(TIMESTAMP(timezone = "True"),server_default = text("NOW()"),nullable = False) # here serve.. =tex... will evaluates NOW() fuction and stores the current tiemstamp in the column
    # created function of storing time is done by database not pythonoralchemy it only works when no value is sent to the column for created time

class Questions(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, unique=True, nullable=False,index = True)
    question_text = Column(String, unique=False, nullable = False)
    answer_text = Column(String, unique=False, nullable = False)
    difficulty_level = Column(String, unique=False, nullable = False)
    topic = Column(String, unique=False, nullable = False)
    created_at = Column(TIMESTAMP(timezone = "True"),server_default = text("NOW()"),nullable = False)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Raw text inputs
    cv_raw = Column(Text, nullable=False)
    job_description_raw = Column(Text, nullable=False)

    # Structured LLM outputs
    cv_parsed = Column(JSONB, nullable=True)
    job_description_parsed = Column(JSONB, nullable=True)
    match_analysis = Column(JSONB, nullable=True)
    interview_questions = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone = "True"),server_default = text("NOW()"),nullable = False) # here serve.. =tex... will evaluates NOW() fuction and stores the current tiemstamp in the column
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"), nullable=False)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)

    # Session details
    job_title = Column(String, nullable=True)
    job_description = Column(Text, nullable=True)
    questions = Column(JSONB, nullable=False)  # Array of question objects
    status = Column(String, nullable=False, server_default="in-progress")  # in-progress, completed, abandoned

    # Timestamps
    start_time = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False)
    end_time = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"), nullable=False)


class InterviewResponse(Base):
    __tablename__ = "interview_responses"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    question_id = Column(String, nullable=False)  # ID from the questions array
    
    # Response data
    answer = Column(Text, nullable=True)
    duration = Column(Integer, nullable=False)  # Duration in seconds
    audio_url = Column(String, nullable=True)  # URL to stored audio file
    video_url = Column(String, nullable=True)  # URL to stored video file
    
    # Analysis results (populated later)
    analysis = Column(JSONB, nullable=True)  # Sentiment, keywords, score, etc.
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False)