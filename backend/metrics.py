from .db import get_audit
def summary():
    logs = get_audit()
    runs = [l for l in logs if l["actor"]=="AGENT" and l["action"] in ("run","run_graph")]
    fails = sum(len(l["payload"].get("errors", [])) for l in runs if isinstance(l["payload"], dict))
    passed = sum(1 for r in runs if r["payload"].get("review",{}).get("passed"))
    return {"runs":len(runs), "review_passed":passed, "tool_failures":fails}