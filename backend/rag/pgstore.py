from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer
import os, math

PG_URL = os.getenv("PG_URL", "postgresql+psycopg2://regops:regops@db:5432/regops")
engine = create_engine(PG_URL, future=True)
_model = None

def model():
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model

def setup():
    with engine.begin() as con:
        con.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    with engine.begin() as con:
        con.execute(text("""
        CREATE TABLE IF NOT EXISTS sop_chunks(
          id BIGSERIAL PRIMARY KEY,
          doc_name TEXT,
          chunk_no INT,
          text TEXT,
          embedding VECTOR(384)
        )"""))


def embed(texts): return model().encode(texts, normalize_embeddings=True).tolist()

def ingest_doc(name: str, content: str, chunk_size=700, overlap=100):
    setup()
    tokens = content.split()
    chunks, i = [], 0
    while i < len(tokens):
        chunk = " ".join(tokens[i:i+chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    vecs = embed(chunks)
    with engine.begin() as con:
        for idx, (t, v) in enumerate(zip(chunks, vecs)):
            con.execute(text("INSERT INTO sop_chunks(doc_name,chunk_no,text,embedding) VALUES (:n,:i,:t,:e)"),
                        {"n": name, "i": idx, "t": t, "e": v})

def search(query: str, k=5):
    setup()
    qv = embed([query])[0]
    with engine.begin() as con:
        rows = con.execute(text("""
        SELECT doc_name, chunk_no, text
        FROM sop_chunks
        ORDER BY embedding <#> CAST(:qv AS vector)  -- cosine distance, normalized
        LIMIT :k
        """), {"qv": qv, "k": k}).mappings().all()
    return rows
