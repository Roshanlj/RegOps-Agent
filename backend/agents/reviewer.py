from ..rag.sop_rules import REQUIRED_FIELDS
from datetime import datetime

def check(run):
    steps = run.get("steps", [])
    email = next((s for s in steps if s["action"]=="mailer.draft_email" and s.get("result")), None)
    lims = next((s for s in steps if s["action"]=="lims.create_pull_list" and s.get("result")), None)

    ok, messages = True, []

    # EMAIL fields
    if email:
        table = email["result"].get("table", [])
        if not table or not all(k in table[0] for k in REQUIRED_FIELDS):
            ok = False; messages.append("EMAIL_02: missing required fields")

        if not email["result"].get("citations"):
            ok = False; messages.append("EMAIL_02: missing citations")

    # Window + two-person review (metadata simulated)
    meta = (lims or {}).get("result", {})
    within_window = meta.get("within_window", True)  # assume true in MVP
    two_person = meta.get("two_person_review", False)
    if not within_window:
        ok = False; messages.append("STAB_01: date not within ±3 days")
    if not two_person:
        ok = False; messages.append("STAB_01: two-person review not confirmed")

    return {"passed": ok, "messages": messages}
