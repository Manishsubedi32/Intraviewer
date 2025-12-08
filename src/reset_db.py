from src.db.database import engine, Base
# Import all your models here so SQLAlchemy knows about them
from src.models.models import User 

def reset_database():
    print("⚠️  Resetting database...")
    

    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    

    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database reset complete.")

if __name__ == "__main__":
    reset_database()


# to run this script, use the command:
# python -m src.reset_db