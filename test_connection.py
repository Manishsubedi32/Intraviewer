import sys
import os

# dynamic import to make sure src is in path
sys.path.append(os.getcwd())

from src.db.database import test_database_connection
from dotenv import load_dotenv

load_dotenv()

print("Testing database connection...")
success, message = test_database_connection()
print(message)

if success:
    print("Connection successful! You can now run the server.")
else:
    print("Connection failed. Please check your credentials.")
