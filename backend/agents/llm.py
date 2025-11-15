import re
import json
import logging
from datetime import date

from backend.llm import get_manager, AllProvidersFailedError

logger = logging.getLogger("regops.agents.llm")


def _extract_week(instr: str) -> str:
    """Extract week number from instruction string"""
    m = re.search(r'(\d{4})-?w(\d{1,2})', instr.lower()) or re.search(r'week\s*([0-9]{1,3})', instr.lower())
    if m:
        n = int(m.group(2) if m.lastindex==2 else m.group(1))
        return str(((n-1) % 53)+1)
    return str(date.today().isocalendar().week)


def _get_planning_prompt(instruction: str) -> tuple[str, str]:
    """
    Generate system and user prompts for LLM planning
    
    Args:
        instruction: User instruction for the agent
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = (
        "You output ONLY JSON with a 'plan' array of tool steps.\n"
        "Tools: lims.create_pull_list{week}, sheets.append_rows{}, "
        "jira.create_issue{summary,labels,idem_key}, "
        "mailer.draft_email{to,subject,body}. "
        "Include week, idem_key='stability-week-<week>'."
    )
    
    user_prompt = f'Instruction: "{instruction}"\nReturn JSON only.'
    
    return system_prompt, user_prompt


def _parse_plan_response(response: str) -> list[dict]:
    """
    Parse LLM response into plan structure
    
    Args:
        response: Raw LLM response text
        
    Returns:
        List of tool step dictionaries
        
    Raises:
        json.JSONDecodeError: If response is not valid JSON
        KeyError: If response doesn't contain 'plan' key
    """
    # Strip markdown code blocks if present
    cleaned = response.strip()
    cleaned = re.sub(r"^```json|```$", "", cleaned, flags=re.I|re.M).strip()
    
    # Parse JSON and extract plan
    parsed = json.loads(cleaned)
    return parsed["plan"]


def _deterministic_plan(instruction: str) -> list[dict]:
    """
    Generate deterministic plan without LLM (fallback)
    
    Args:
        instruction: User instruction for the agent
        
    Returns:
        List of tool step dictionaries
    """
    w = _extract_week(instruction)
    idem = f"stability-week-{w}"
    
    return [
        {"tool": "lims.create_pull_list", "args": {"week": w}},
        {"tool": "sheets.append_rows"},
        {"tool": "jira.create_issue", "args": {
            "summary": f"Weekly stability pulls prepared (W{w})",
            "labels": ["stability", f"week{w}"],
            "idem_key": idem
        }},
        {"tool": "mailer.draft_email", "args": {
            "to": ["qa@example.com"],
            "subject": f"Week {w} stability pull list",
            "body": "See table below"
        }}
    ]


def plan_for(instruction: str, state) -> list[dict]:
    """
    Generate execution plan for given instruction
    
    Args:
        instruction: User instruction for the agent
        state: Agent state (unused but kept for compatibility)
        
    Returns:
        List of tool step dictionaries
    """
    try:
        # Try to use LLM manager
        manager = get_manager()
        system_prompt, user_prompt = _get_planning_prompt(instruction)
        
        logger.info("Attempting to generate plan using LLM")
        response = manager.chat(system_prompt, user_prompt)
        plan = _parse_plan_response(response)
        logger.info(f"Successfully generated plan with {len(plan)} steps")
        return plan
        
    except AllProvidersFailedError as e:
        # All LLM providers failed, use deterministic fallback
        logger.warning(f"All LLM providers failed, using deterministic fallback: {e}")
        return _deterministic_plan(instruction)
        
    except Exception as e:
        # Any other error (parsing, etc.), use deterministic fallback
        logger.warning(f"Error generating LLM plan, using deterministic fallback: {e}")
        return _deterministic_plan(instruction)
