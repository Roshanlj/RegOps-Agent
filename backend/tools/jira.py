from ..db import add_audit
_seen = set()  # replace with sqlite later

def create_issue(summary: str, labels=None, assignee=None, due_days=2, idem_key=None):
    key = idem_key or f"{summary}|{tuple(labels or [])}"
    if key in _seen:
        return {"key":"JIRA-EXISTING", "summary":summary, "labels":labels or []}
    _seen.add(key)
    payload = {"summary": summary, "labels": labels or [], "assignee": assignee, "due_days": due_days}
    add_audit("JIRA","create_issue",payload)
    return {"key":"JIRA-1001", **payload}