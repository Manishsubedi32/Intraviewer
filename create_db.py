import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

passwords = ["manish123", "postgres", "admin", "password"]

for password in passwords:
    try:
        print(f"Trying password: {password}")
        con = psycopg2.connect(dbname='postgres', user='postgres', host='localhost', password=password)
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()
        cur.execute('CREATE DATABASE intraviewer_db;')
        print("Database 'intraviewer_db' created successfully.")
        cur.close()
        con.close()
        break
    except psycopg2.errors.DuplicateDatabase:
        print("Database 'intraviewer_db' already exists.")
        break
    except Exception as e:
        print(f"Failed with password '{password}': {e}")
