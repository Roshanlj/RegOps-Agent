from ..db import add_audit
_fail_once = {"done": False}

def create_pull_list(week: str):
    # Fail only on the first call to simulate a transient/system issue
    if not _fail_once["done"]:
        _fail_once["done"] = True
        raise RuntimeError("LIMS timeout (simulated)")
    payload = {
        "week": week,
        "items":[
            {"Lot":"L001","Batch":f"B-{week}-01","Expiry":"2026-03","Storage":"2-8C"},
            {"Lot":"L002","Batch":f"B-{week}-02","Expiry":"2026-06","Storage":"25C"}
        ],
        "within_window": True,
        "two_person_review": True
    }
    add_audit("LIMS","create_pull_list",payload)
    return payload
