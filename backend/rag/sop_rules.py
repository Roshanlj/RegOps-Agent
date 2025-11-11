def sop_rules():
    return [
        {"id":"STAB_01","if":"stability_pull",
         "must":[
            "date_within_window",
            "two_person_review"
         ]},
        {"id":"EMAIL_02","if":"send_email",
         "must":[
            "includes_required_fields",
            "has_citations"
         ]},
    ]

REQUIRED_FIELDS = ["Lot","Batch","Expiry","Storage"]
