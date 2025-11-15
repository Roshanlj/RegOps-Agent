from langgraph.graph import StateGraph, START, END
from typing import Dict, Any, List
from . import tool_exec, reviewer
from .llm import plan_for
from .toolspec import validate_action
from backend.llm import get_manager

MAX_ITERS = 3
State = Dict[str, Any]  # simple state for legacy API

def node_iter(state: State) -> State:
    state = dict(state)
    state["iter"] = int(state.get("iter", 0)) + 1
    return state

def node_plan(state: State) -> State:
    state = dict(state)
    plan = plan_for(state["instruction"], state)
    validated = []
    for step in plan:
        action = step["tool"]
        args = validate_action(action, step.get("args", {}))
        validated.append({"tool": action, "args": args})
    state["plan"] = validated
    
    # Capture which LLM provider was used for audit trail
    try:
        manager = get_manager()
        state["llm_provider"] = manager.last_used_provider or "deterministic"
    except Exception:
        # If manager not available or error, mark as deterministic
        state["llm_provider"] = "deterministic"
    
    return state

def node_exec(state: State) -> State:
    state = dict(state)
    steps, ctx, errors = [], {}, []
    for i, st in enumerate(state.get("plan", []), start=1):
        sid = f"plan-{i}"
        try:
            res = tool_exec.execute({"action": st["tool"], "args": st.get("args", {})}, ctx)
            ctx[sid] = res
            steps.append({"id": sid, "action": st["tool"], "result": res})
        except Exception as e:
            msg = str(e)
            steps.append({"id": sid, "action": st["tool"], "error": msg})
            errors.append({"id": sid, "action": st["tool"], "error": msg})
    state["steps"] = steps
    state["errors"] = errors
    return state

def node_review(state: State) -> State:
    state = dict(state)
    state["review"] = reviewer.check({"steps": state.get("steps", [])})
    return state

def should_replan(state: State) -> str:
    if int(state.get("iter", 0)) >= MAX_ITERS:
        return "done"
    if state.get("errors"):
        return "loop"
    if not state.get("review", {}).get("passed", False):
        return "loop"
    return "done"

def build():
    g = StateGraph(dict)
    g.add_node("iter", node_iter)
    g.add_node("plan", node_plan)
    g.add_node("exec", node_exec)
    g.add_node("review", node_review)
    g.add_edge(START, "iter")
    g.add_edge("iter", "plan")
    g.add_edge("plan", "exec")
    g.add_edge("exec", "review")
    g.add_conditional_edges("review", should_replan, {"loop": "iter", "done": END})
    return g.compile()

GRAPH = build()
