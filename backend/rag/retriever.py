from .sop_rules import REQUIRED_FIELDS
from .. import db

def answer_with_citations(question: str):
    # Naive retrieval over stored docs
    ctx = db.search_docs(question, k=3)
    if not ctx:
        return {"answer":"I don't have sufficient SOP context to answer.", "citations":[]}
    # Very naive "answer": echo relevant snippets
    snippets = []
    for c in ctx:
        content = c["content"]
        # take lines that have any keyword
        lines = [ln for ln in content.splitlines() if any(tok.lower() in ln.lower() for tok in question.split())]
        if not lines:
            lines = content.splitlines()[:2]
        snippets.extend(lines[:3])
    answer = "\n".join(snippets[:6])
    # Build citations as doc names
    citations = [{"doc": c["name"]} for c in ctx]
    return {"answer": answer, "citations": citations}
