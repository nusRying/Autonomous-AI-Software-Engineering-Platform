
import sqlite3
import os

def check_db():
    db_file = "audit_platform.db"
    print(f"Checking {db_file} in {os.getcwd()}")
    if not os.path.exists(db_file):
        print("Database file NOT FOUND!")
        return

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables: {tables}")
    
    if "audit_jobs" in tables:
        cursor.execute("SELECT COUNT(*) FROM audit_jobs")
        count = cursor.fetchone()[0]
        print(f"audit_jobs count: {count}")
        
        if count > 0:
            cursor.execute("SELECT job_id, status, error FROM audit_jobs ORDER BY created_at DESC LIMIT 5")
            rows = cursor.fetchall()
            for row in rows:
                print(f"Job: {row[0]} | Status: {row[1]} | Error: {row[2]}")
    
    conn.close()

if __name__ == "__main__":
    check_db()
