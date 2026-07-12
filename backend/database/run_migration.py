"""
database/run_migration.py — Runs the SQL migration scripts to initialize Postgres tables
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2

# Add parent directory to path so we can load config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_migration():
    # Load environment variables
    load_dotenv()
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set in the .env file.")
        return False
        
    print(f"Connecting to database: {db_url.split('@')[-1]}")
    
    # Read sql script
    migration_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file_path = os.path.join(migration_dir, "migrations", "init_schema.sql")
    
    if not os.path.exists(sql_file_path):
        print(f"Migration file not found at: {sql_file_path}")
        return False
        
    with open(sql_file_path, "r", encoding="utf-8") as f:
        sql_content = f.read()
        
    # Connect and run
    try:
        # Connect to postgres server first to ensure DB exists, if not, create it
        # Parse params from URL
        # For simplicity, we directly connect to the target database. If database does not exist,
        # we connect to default database 'postgres' first and create it.
        
        # Connect to default postgres to check if target db exists
        db_user = os.getenv("DB_USER", "postgres")
        db_pass = os.getenv("DB_PASSWORD", "9699")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "ai_pm_copilot")
        
        conn = psycopg2.connect(
            user=db_user,
            password=db_pass,
            host=db_host,
            port=db_port,
            database="postgres"
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check database existence
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}';")
        exists = cur.fetchone()
        if not exists:
            print(f"Database '{db_name}' does not exist. Creating...")
            cur.execute(f"CREATE DATABASE {db_name};")
            print("Database created successfully.")
        else:
            print(f"Database '{db_name}' already exists.")
            
        cur.close()
        conn.close()
        
        # Now connect to target database and execute migrations
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Running SQL script initialization...")
        # Execute the entire script. Psycopg2 cursor.execute can run multiple statements separated by semicolons
        cur.execute(sql_content)
        print("Migration executed successfully.")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
