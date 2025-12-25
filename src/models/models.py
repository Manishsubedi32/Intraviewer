from typing import Text
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from sqlalchemy.sql.sqltypes import TIMESTAMP,Time
from src.db.database import Base
import enum #to define enum for user roles if needed meaning only specific roles are allowed

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
class SessionStatus(str, enum.Enum):
    ONGOING = "ongoing"
    COMPLETED = "completed"
    ANALYSING = "analyzing"
    TERMINATED = "terminated"

class IsActive(str, enum.Enum):
    TRUE = "True"
    FALSE = "False"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, unique=True, nullable=False,index = True)
    firstname = Column(String, unique=False, nullable = False)
    lastname = Column(String, unique=False, nullable = False)
    email = Column(String, unique=True, nullable = False)
    password = Column(String, nullable = False)
    role = Column(Enum(UserRole), nullable = False, server_default=text("'USER'"))
    is_active = Column(Boolean, server_default=text("True"), nullable=False)
    created_at = Column(TIMESTAMP(timezone = "True"),server_default = text("NOW()"),nullable = False) # here serve.. =tex... will evaluates NOW() fuction and stores the current tiemstamp in the column
    # created function of storing time is done by database not pythonoralchemy it only works when no value is sent to the column for created time

class Questions(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, unique=True, nullable=False,index = True)
    question_text = Column(String, unique=False, nullable = False)
    session_id = Column(Integer, ForeignKey("session.id", ondelete="CASCADE"), nullable=False) # ADDED THIS
    difficulty_level = Column(Enum(DifficultyLevel), unique=False, nullable = True)
    order = Column(Integer)
    created_at = Column(TIMESTAMP(timezone = "True"),server_default = text("NOW()"),nullable = False)
    session = relationship("InterviewSession", back_populates="questions")
    
class InterviewSession(Base):
    __tablename__ = "session"
    id = Column(Integer, primary_key=True, unique=True, nullable=False,index = True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    cv_id = Column(Integer, ForeignKey("cv_uploads.id", ondelete="SET NULL"), nullable=True)
    prompt_id = Column(Integer, ForeignKey("text_prompts.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(SessionStatus), unique=False, nullable = False, server_default=text("'ONGOING'")) # ongoing, completed, terminated
    start_time = Column(TIMESTAMP(timezone = "True"),server_default = text("NOW()"),nullable = False)
    final_score = Column(Integer, unique=False, nullable = True)
    analysis = Column(Text, unique=False, nullable = True) # for storing analysis of answer by 
    questions = relationship("Questions", back_populates="session")
    transcripts = relationship("Transcript", back_populates="session")
    if status == SessionStatus.COMPLETED:
        end_time = Column(TIMESTAMP(timezone = "True"),nullable = True)

class Cv(Base):
    __tablename__ = "cv_uploads"
    id = Column(Integer, primary_key=True, unique=True, nullable=False,index = True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    CV_data:bytes = Column(LargeBinary, unique=False, nullable = False) # storing cv as bytes
    cv_text = Column(String, unique=False, nullable = False) # extracted text from the cv for further processing
    uploaded_at = Column(TIMESTAMP(timezone = "True"),server_default = text("NOW()"),nullable = False)

class TextPrompts(Base):
    __tablename__ = "text_prompts"
    id = Column(Integer, primary_key=True, unique=True, nullable=False,index = True)
    name = Column(String, unique=False, nullable = False) # eg. "python job interview" , "visa interview","college interview"etc
    prompt_text = Column(String, unique=False, nullable = False)
    created_at = Column(TIMESTAMP(timezone = "True"),server_default = text("NOW()"),nullable = False)

class LiveChunksInput(Base): # here we will store live audio chunks to send to whisper and live video to send to emotion detection model
    __tablename__ = "live_chunks_input"
    id = Column(Integer, primary_key=True, unique=True, nullable=False,index = True)
    session_id = Column(Integer, ForeignKey("session.id", ondelete="CASCADE"), nullable=False)
    audio_chunk:bytes = Column(String, unique=False, nullable = True) # storing audio chunk as bytes # might delete after the interview is over cause not required
    video_chunk:bytes = Column(String, unique=False, nullable = True) # storing video chunk as bytes # sent to the emotion detection so can't delete
    created_at = Column(TIMESTAMP(timezone = "True"),server_default = text("NOW()"),nullable = False)

class Transcript(Base): # now here our whisper sent user_response and ai_response to backend will be stored
    __tablename__ = "transcripts"
    id = Column(Integer, primary_key=True, unique=True, nullable=False,index = True)
    session_id = Column(Integer, ForeignKey("session.id", ondelete="CASCADE"), nullable=False) #multiple transcripts can belong to one session
    is_ai_response = Column(Boolean, unique=False, nullable = False,default=False) # to identify if the transcript is from ai or user
    ai_response = Column(String, unique=False, nullable = True)
    user_response = Column(String, unique=False, nullable = True)
    created_at = Column(TIMESTAMP(timezone = "True"),server_default = text("NOW()"),nullable = False)
    session = relationship("InterviewSession", back_populates="transcripts") # this allows us to access session from transcript and vice versa eg my_transcript.session.user_id