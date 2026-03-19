
import sqlite3
import redis

def check_state():
    print("--- Database State ---")
    conn = sqlite3.connect("audit_platform.db")
    cursor = conn.cursor()
    cursor.execute("SELECT job_id, status, error FROM audit_jobs ORDER BY created_at DESC LIMIT 5")
    rows = cursor.fetchall()
    for row in rows:
        print(f"Job: {row[0]} | Status: {row[1]} | Error: {row[2]}")
    conn.close()

    print("\n--- Redis State ---")
    try:
        r = redis.from_url("redis://localhost:6379/0")
        keys = r.keys("*")
        print(f"Total keys: {len(keys)}")
        for key in keys:
            print(f"Key: {key}")
            # Check celery queue
            if b"celery" in key:
                 length = r.llen(key)
                 print(f"  Queue length: {length}")
    except Exception as e:
        print(f"Redis error: {e}")

if __name__ == "__main__":
    check_state()
