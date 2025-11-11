import sqlite3, os, time, json

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

def add_audit(actor: str, action: str, payload: dict):
    _ensure()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO audit(ts,actor,action,payload) VALUES(?,?,?,?)",
                  (time.time(), actor, action, json.dumps(payload)))
        conn.commit()

def get_audit():
    _ensure()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        rows = c.execute("SELECT id, ts, actor, action, payload FROM audit ORDER BY id DESC LIMIT 500").fetchall()
    return [
        {"id": r[0], "ts": r[1], "actor": r[2], "action": r[3], "payload": json.loads(r[4])}
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
