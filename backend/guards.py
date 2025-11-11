import re
PII = [re.compile(r"\b\d{10}\b"), re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)]
def redact(s:str)->str:
    for rx in PII: s = rx.sub("[REDACTED]", s)
    return s
