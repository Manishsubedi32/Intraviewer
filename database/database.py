import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

DATABASE_URL = f"postgresql+psycopg://{os.getenv('DB_USERNAME', 'user')}:{os.getenv('DB_PASSWORD', 'password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'intraviewer_db')}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_database_connection():
    """Test if database connection is working"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return True, "Database connection successful"
    except SQLAlchemyError as e:
        return False, f"Database connection failed: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"