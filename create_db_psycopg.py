import psycopg
from psycopg import OperationalError

passwords = ["manish123", "postgres", "admin", "password"]

for password in passwords:
    try:
        print(f"Trying connection with password: {password}")
        # Note: psycopg autocommits by default for top-level statements like CREATE DATABASE
        # but connecting to 'postgres' db is standard practice to create another db
        # If autocommit is needed explicitly: conn.autocommit = True
        
        with psycopg.connect(
            dbname="postgres",
            user="postgres",
            password=password,
            host="localhost",
            port="5432",
            autocommit=True  # Important for CREATE DATABASE
        ) as conn:
            with conn.cursor() as cur:
                # Check if database exists first instead of blindly creating
                cur.execute("SELECT 1 FROM pg_database WHERE datname = 'intraviewer_db'")
                exists = cur.fetchone()
                if not exists:
                    cur.execute("CREATE DATABASE intraviewer_db")
                    print("Database 'intraviewer_db' created successfully.")
                else:
                    print("Database 'intraviewer_db' already exists.")
        break  # If successful connection, break loop
    except OperationalError as e:
        print(f"Failed with password '{password}': {e}")
    except Exception as e:
        print(f"An error occurred with password '{password}': {e}")
