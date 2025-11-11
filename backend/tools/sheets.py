from ..db import add_audit

_TRACKER = []

def append_rows(rows):
    global _TRACKER
    _TRACKER.extend(rows)
    payload = {"rows": rows, "count": len(rows)}
    add_audit("SHEETS","append_rows",payload)
    return {"ok": True, **payload}
