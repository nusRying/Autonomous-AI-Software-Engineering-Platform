import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = 'audit_platform.db'

def seed_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        api_key TEXT NOT NULL,
        label TEXT,
        is_active BOOLEAN DEFAULT 1,
        token_limit INTEGER,
        tokens_used INTEGER DEFAULT 0,
        total_usage_cost FLOAT DEFAULT 0.0,
        disabled_until DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_id INTEGER NOT NULL,
        model TEXT NOT NULL,
        tokens_in INTEGER DEFAULT 0,
        tokens_out INTEGER DEFAULT 0,
        cost FLOAT DEFAULT 0.0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (key_id) REFERENCES api_keys (id)
    )
    """)
    
    # Seed Keys
    cursor.execute("SELECT COUNT(*) FROM api_keys")
    if cursor.fetchone()[0] == 0:
        print("Seeding dummy keys...")
        cursor.execute("INSERT INTO api_keys (provider, api_key, label) VALUES (?, ?, ?)", ("openai", "sk-...", "Main OpenAI"))
        cursor.execute("INSERT INTO api_keys (provider, api_key, label) VALUES (?, ?, ?)", ("anthropic", "sk-ant-...", "Anthropic Key"))
        cursor.execute("INSERT INTO api_keys (provider, api_key, label) VALUES (?, ?, ?)", ("google", "ai-...", "Gemini Pro"))
    
    # Get key IDs
    cursor.execute("SELECT id, provider FROM api_keys")
    keys = cursor.fetchall()
    
    # Seed Usage
    cursor.execute("SELECT COUNT(*) FROM api_usage")
    if cursor.fetchone()[0] == 0:
        print("Seeding dummy usage logs...")
        today = datetime.now()
        for i in range(14): # 2 weeks
            day = today - timedelta(days=i)
            # Create a few logs per day per key
            for key_id, provider in keys:
                num_logs = random.randint(1, 5)
                for _ in range(num_logs):
                    t_in = random.randint(500, 2000)
                    t_out = random.randint(200, 1000)
                    cursor.execute(
                        "INSERT INTO api_usage (key_id, model, tokens_in, tokens_out, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (key_id, f"{provider}-model", t_in, t_out, day.isoformat())
                    )
    
    conn.commit()
    print("Seed complete.")
    conn.close()

if __name__ == "__main__":
    seed_data()
