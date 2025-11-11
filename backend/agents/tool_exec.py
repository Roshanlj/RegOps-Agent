from ..tools import lims, jira, mailer, sheets
from ..rag.retriever import answer_with_citations

def execute(step, context):
    action = step["action"]
    if action == "lims.create_pull_list":
        res = lims.create_pull_list(week=step.get("args",{}).get("week",""))
        return res
    if action == "sheets.append_rows":
        # pull rows from previous step result
        rows = context.get("plan-1",{}).get("items",[])
        return sheets.append_rows(rows)
    if action == "jira.create_issue":
        return jira.create_issue(**step.get("args",{}))
    if action == "mailer.draft_email":
        # build table from LIMS output
        table = context.get("plan-1",{}).get("items",[])
        # naive citations: echo doc names that matched "stability pulls"
        ans = answer_with_citations("stability pulls required email content")
        return mailer.draft_email(table=table, citations=ans.get("citations",[]), **step.get("args",{}))
    if action == "rag.answer":
        return answer_with_citations(step.get("args",{}).get("question",""))
    raise ValueError(f"Unknown action: {action}")
