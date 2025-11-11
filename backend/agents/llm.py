import os, re, json, requests
BASE = os.getenv("LLM_BASE_URL")  # e.g., http://host.docker.internal:1234/v1
MODEL = os.getenv("LLM_MODEL", "local")

def _openai_chat(system: str, user: str) -> str:
    r = requests.post(f"{BASE}/chat/completions", json={
        "model": MODEL,
        "messages": [{"role":"system","content":system},{"role":"user","content":user}],
        "temperature": 0
    }, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def _extract_week(instr: str) -> str:
    m = re.search(r'(\d{4})-?w(\d{1,2})', instr.lower()) or re.search(r'week\s*([0-9]{1,3})', instr.lower())
    if m:
        n = int(m.group(2) if m.lastindex==2 else m.group(1))
        return str(((n-1) % 53)+1)
    from datetime import date
    return str(date.today().isocalendar().week)

def _llm_plan(instruction: str) -> list[dict]:
    sys = ("You output ONLY JSON with a 'plan' array of tool steps.\n"
           "Tools: lims.create_pull_list{week}, sheets.append_rows{}, jira.create_issue{summary,labels,idem_key}, "
           "mailer.draft_email{to,subject,body}. Include week, idem_key='stability-week-<week>'.")
    user = f'Instruction: "{instruction}"\nReturn JSON only.'
    txt = _openai_chat(sys, user).strip()
    txt = re.sub(r"^```json|```$", "", txt, flags=re.I|re.M).strip()
    return json.loads(txt)["plan"]

def plan_for(instruction: str, state) -> list[dict]:
    if BASE:
        try:
            return _llm_plan(instruction)
        except Exception:
            pass
    # deterministic fallback (no LLM)
    w = _extract_week(instruction); idem = f"stability-week-{w}"
    return [
      {"tool":"lims.create_pull_list","args":{"week": w}},
      {"tool":"sheets.append_rows"},
      {"tool":"jira.create_issue","args":{"summary": f"Weekly stability pulls prepared (W{w})","labels":["stability",f"week{w}"],"idem_key": idem}},
      {"tool":"mailer.draft_email","args":{"to":["qa@example.com"],"subject": f"Week {w} stability pull list","body":"See table below"}}
    ]
