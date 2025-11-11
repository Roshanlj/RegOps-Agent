from pydantic import BaseModel, Field
from typing import Any, Dict

class LimsCreatePullList(BaseModel):
    # allow up to 3 digits; we normalize in planner
    week: str = Field(..., pattern=r"^\d{1,3}$")

class JiraCreateIssue(BaseModel):
    summary: str
    labels: list[str] = []
    assignee: str | None = None
    due_days: int = 2
    idem_key: str | None = None  # <- support idempotency

class MailDraftEmail(BaseModel):
    to: list[str]
    subject: str
    body: str

SCHEMAS: Dict[str, BaseModel] = {
    "lims.create_pull_list": LimsCreatePullList,
    "jira.create_issue": JiraCreateIssue,
    "mailer.draft_email": MailDraftEmail,
    "sheets.append_rows": BaseModel,   # no args; rows come from context
}

def validate_action(action: str, args: Dict[str, Any]) -> Dict[str, Any]:
    schema = SCHEMAS.get(action)
    if schema is BaseModel:  # pass-through
        return args or {}
    if schema is None:
        raise ValueError(f"Unknown action: {action}")
    try:
        return schema(**(args or {})).model_dump()
    except ValidationError as e:
        raise ValueError(f"Invalid args for {action}: {e.errors()}")
