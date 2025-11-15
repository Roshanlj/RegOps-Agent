import sqlite3, os, time, json
import logging

logger = logging.getLogger("regops.db")

DB_PATH = os.environ.get("COPILOT_DB", "data/copilot.sqlite3")

def _ensure():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS docs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            content TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL,
            actor TEXT,
            action TEXT,
            payload TEXT
        )""")
        conn.commit()

def init_db():
    """Run database migrations"""
    _ensure()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        
        # Migration: Add llm_provider column to audit table
        try:
            # Check if column exists
            c.execute("PRAGMA table_info(audit)")
            columns = [col[1] for col in c.fetchall()]
            
            if 'llm_provider' not in columns:
                logger.info("Adding llm_provider column to audit table")
                c.execute("ALTER TABLE audit ADD COLUMN llm_provider TEXT")
                conn.commit()
                logger.info("Successfully added llm_provider column")
        except Exception as e:
            logger.error(f"Failed to add llm_provider column: {e}")
            # Don't raise - allow app to continue if migration fails

def add_audit(actor: str, action: str, payload: dict, provider: str = None):
    """
    Add audit log entry
    
    Args:
        actor: User or system performing the action
        action: Action being performed
        payload: Action details as dict
        provider: Optional LLM provider name used for this action
    """
    _ensure()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO audit(ts,actor,action,payload,llm_provider) VALUES(?,?,?,?,?)",
                  (time.time(), actor, action, json.dumps(payload), provider))
        conn.commit()

def get_audit():
    _ensure()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        rows = c.execute("SELECT id, ts, actor, action, payload, llm_provider FROM audit ORDER BY id DESC LIMIT 500").fetchall()
    return [
        {"id": r[0], "ts": r[1], "actor": r[2], "action": r[3], "payload": json.loads(r[4]), "llm_provider": r[5]}
        for r in rows
    ]

def add_doc(name: str, content: str):
    _ensure()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO docs(name, content) VALUES(?,?)", (name, content))
        conn.commit()

def search_docs(query: str, k: int = 3):
    _ensure()
    q = query.lower()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        rows = c.execute("SELECT id, name, content FROM docs").fetchall()
    scored = []
    for _id, name, content in rows:
        text = (content or "").lower()
        score = sum(text.count(tok) for tok in q.split())
        if score > 0:
            scored.append((_id, name, content, score))
    scored.sort(key=lambda x: x[3], reverse=True)
    return [{"id": s[0], "name": s[1], "content": s[2]} for s in scored[:k]]

# Run migrations on module import
init_db()
