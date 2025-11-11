# Simple, dependency-free eval:
# - Retrieves top-k chunks via pgstore.search (same as /ask_rag)
# - Scores whether expected keywords (from `ground`) appear in the retrieved context.

from ..rag import pgstore

def _norm(s: str) -> set:
    return set(w.lower() for w in s.replace(",", " ").split())

def eval_rag(cases, k=5):
    results = []
    for c in cases:
        q = c["question"]
        ground = _norm(c.get("ground",""))
        hits = pgstore.search(q, k=k) or []
        ctx = " ".join(h["text"] for h in hits)
        ctx_tokens = _norm(ctx)
        found = {w for w in ground if w in ctx_tokens}
        coverage = (len(found) / len(ground)) if ground else 0.0  # “recall”-like
        precision_proxy = (len(found) / (len(ctx_tokens) or 1))   # very rough
        results.append({
            "question": q,
            "ground_count": len(ground),
            "found_count": len(found),
            "coverage": round(coverage, 3),
            "precision_proxy": round(precision_proxy, 3),
            "found_terms": sorted(found),
            "citations": [{"doc": h["doc_name"], "chunk": h["chunk_no"]} for h in hits],
        })
    # Aggregate quick summary
    avg_cov = round(sum(r["coverage"] for r in results)/len(results), 3) if results else 0.0
    return {"avg_coverage": avg_cov, "cases": results}
