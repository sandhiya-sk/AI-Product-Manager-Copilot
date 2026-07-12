"""
database/seed.py — Seeds the database with default users for testing
"""

import os
import sys
import uuid
import bcrypt
from dotenv import load_dotenv
import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def seed():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("DATABASE_URL is not set.")
        return False
        
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if users already exist
        cur.execute("SELECT COUNT(*) FROM users;")
        count = cur.fetchone()[0]
        
        if count > 0:
            print("Database already contains users. Seeding skipped.")
            cur.close()
            conn.close()
            return True
            
        # Seed default PM user
        pm_email = "pm@company.com"
        pm_password = "password123"
        hashed = bcrypt.hashpw(pm_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        pm_id = str(uuid.uuid4())
        project_id = "550e8400-e29b-41d4-a716-446655440000"
        
        cur.execute(
            "INSERT INTO users (user_id, email, password_hash, full_name, role, project_id, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (pm_id, pm_email, hashed, "Jane Product Manager", "product_manager", project_id, True)
        )
        print(f"Seeded default PM User: {pm_email} / {pm_password}")
        
        # Seed default Customer user
        cust_email = "customer@example.com"
        cust_password = "password123"
        hashed_cust = bcrypt.hashpw(cust_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cust_id = str(uuid.uuid4())
        
        cur.execute(
            "INSERT INTO users (user_id, email, password_hash, full_name, role, project_id, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (cust_id, cust_email, hashed_cust, "John Customer", "customer", project_id, True)
        )
        print(f"Seeded default Customer User: {cust_email} / {cust_password}")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Seeding failed: {e}")
        return False

if __name__ == "__main__":
    seed()
