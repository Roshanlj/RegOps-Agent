def plan(instruction: str):
    inst = instruction.lower()
    steps = []
    if "stability" in inst and "pull" in inst:
        steps = [
            {"id":"plan-1","action":"lims.create_pull_list","args":{"week":"45"}},
            {"id":"plan-2","action":"sheets.append_rows","from":"plan-1.items"},
            {"id":"plan-3","action":"jira.create_issue","args":{"summary":"Weekly stability pulls prepared","labels":["stability","week45"]}},
            {"id":"plan-4","action":"mailer.draft_email","args":{"to":["qa@example.com"],"subject":"Week 45 stability pull list","body":"See table below"}}
        ]
    else:
        steps = [{"id":"plan-1","action":"rag.answer","args":{"question":instruction}}]
    return steps
