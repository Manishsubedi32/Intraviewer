from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from .database import Base

class HealthCheck(Base):
    __tablename__ = "health_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="healthy")
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    message = Column(String, default="Database test entry")
    is_active = Column(Boolean, default=True)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)