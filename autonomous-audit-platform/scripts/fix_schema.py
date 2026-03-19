
import asyncio
import sqlite3
import os

DB_PATH = "./audit_platform.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} does not exist. Skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Check audit_jobs
    cursor.execute("PRAGMA table_info(audit_jobs)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "health_score" not in columns:
        print("Adding health_score to audit_jobs...")
        cursor.execute("ALTER TABLE audit_jobs ADD COLUMN health_score INTEGER")
    
    if "report_data" not in columns:
        print("Adding report_data to audit_jobs...")
        cursor.execute("ALTER TABLE audit_jobs ADD COLUMN report_data JSON")

    if "owner_id" not in columns:
        print("Adding owner_id to audit_jobs...")
        cursor.execute("ALTER TABLE audit_jobs ADD COLUMN owner_id INTEGER REFERENCES users(id)")
    
    # 2. Check engineer_jobs
    cursor.execute("PRAGMA table_info(engineer_jobs)")
    columns = [row[1] for row in cursor.fetchall()]
    if "owner_id" not in columns:
        print("Adding owner_id to engineer_jobs...")
        cursor.execute("ALTER TABLE engineer_jobs ADD COLUMN owner_id INTEGER REFERENCES users(id)")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
