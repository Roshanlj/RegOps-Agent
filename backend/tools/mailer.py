from ..db import add_audit

def draft_email(to, subject, body, table=None, citations=None):
    payload = {"to": to, "subject": subject, "body": body, "table": table or [], "citations": citations or []}
    add_audit("MAILER","draft_email",payload)
    return payload
