
import os, sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("LOG_DB_PATH", "/data/calls.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            caller TEXT,
            called TEXT,
            call_sid TEXT,
            intent TEXT,
            transcript TEXT,
            recording_url TEXT,
            lead_score INTEGER,
            lead_tags TEXT
        )""")
        conn.commit()

def init_events():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            call_id INTEGER,
            event TEXT NOT NULL,
            meta TEXT
        )""")
        conn.commit()

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def insert_call(created_at, caller, called, call_sid, intent, transcript, recording_url):
    with db() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO calls (created_at, caller, called, call_sid, intent, transcript, recording_url)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (created_at, caller, called, call_sid, intent, transcript, recording_url))
        conn.commit()
        return c.lastrowid

def list_calls(limit=100):
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, created_at, caller, called, call_sid, intent, recording_url FROM calls ORDER BY id DESC LIMIT ?", (limit,))
        return c.fetchall()

def get_call(call_id: int):
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, created_at, caller, called, call_sid, intent, transcript, recording_url FROM calls WHERE id=?", (call_id,))
        return c.fetchone()

def add_event(call_id: int, event: str, meta: str = None):
    with db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO events (created_at, call_id, event, meta) VALUES (datetime('now'), ?, ?, ?)", (call_id, event, meta))
        conn.commit()

def metrics_since(days: int = 7):
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(1) FROM calls WHERE created_at >= datetime('now', ?)", (f'-{days} days',))
        calls = c.fetchone()[0]
        c.execute("SELECT intent, COUNT(1) FROM calls WHERE created_at >= datetime('now', ?) GROUP BY intent", (f'-{days} days',))
        intents = dict(c.fetchall())
        c.execute("SELECT AVG(lead_score) FROM calls WHERE created_at >= datetime('now', ?) AND lead_score IS NOT NULL", (f'-{days} days',))
        avg_score = c.fetchone()[0]
        c.execute("SELECT COUNT(1) FROM calls WHERE created_at >= datetime('now', ?) AND lead_score >= 30", (f'-{days} days',))
        hot = c.fetchone()[0]
        return {"calls": calls, "intents": intents, "avg_lead_score": avg_score, "hot_leads": hot}
