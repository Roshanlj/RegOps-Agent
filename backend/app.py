from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from . import db
from .agents import planner, tool_exec, reviewer
from .rag import retriever
from .rag import pgstore
from fastapi.staticfiles import StaticFiles
from . import metrics
from .agents.graph import GRAPH
from pydantic import BaseModel

app = FastAPI(title="RegOps Copilot (MVP)")
app.mount("/app", StaticFiles(directory="backend/static", html=True), name="static")

class AskReq(BaseModel):
    question: str

class TaskReq(BaseModel):
    instruction: str

class AskRagReq(BaseModel):
    question: str
    k: int = 5

class AgentReq(BaseModel): 
    instruction: str

class RagEvalReq(BaseModel):
    cases: list[dict]

RUN_APPROVALS = {}

class ApproveReq(BaseModel): run_id: str; approve: bool

@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8", errors="ignore")
    db.add_doc(file.filename, content)
    db.add_audit("API","ingest",{"name": file.filename, "bytes": len(content)})
    pgstore.ingest_doc(file.filename, content)
    return {"ok": True, "name": file.filename, "size": len(content)}

@app.post("/ask")
def ask(req: AskReq):
    out = retriever.answer_with_citations(req.question)
    db.add_audit("RAG","ask",{"q": req.question, "citations": out.get("citations",[])})
    return out

@app.post("/task")
def task(req: TaskReq):
    steps = planner.plan(req.instruction)
    context: Dict[str, Any] = {}
    run_steps = []
    for s in steps:
        try:
            res = tool_exec.execute(s, context)
            s_out = {**s, "result": res}
            context[s["id"]] = res
        except Exception as e:
            s_out = {**s, "error": str(e)}
        run_steps.append(s_out)
    review = reviewer.check({"steps": run_steps})
    db.add_audit("AGENT","run",{"instruction": req.instruction, "review": review})
    return {"steps": run_steps, "review": review}

@app.get("/audit/logs")
def logs():
    return {"logs": db.get_audit()}

@app.post("/ask_rag")
def ask_rag(req: AskRagReq):
    hits = pgstore.search(req.question, k=req.k)
    answer = "\n".join(h["text"] for h in hits[:3]) if hits else "No context found."
    cites = [{"doc": h["doc_name"], "chunk": h["chunk_no"]} for h in hits]
    db.add_audit("RAG-PGV","ask",{"q": req.question, "cites": cites})
    return {"answer": answer, "citations": cites}

@app.get("/metrics/summary")
def metrics_summary():
    return metrics.summary()

@app.post("/eval/rag")
def eval_rag_api(req: RagEvalReq):
    from .eval.rag_eval import eval_rag
    out = eval_rag(req.cases)
    db.add_audit("EVAL","rag_simple", out)
    return out

@app.post("/agent/run")
def agent_run(req: AgentReq):
    out = GRAPH.invoke({"instruction": req.instruction})
    llm_provider = out.get("llm_provider", "deterministic")
    db.add_audit("AGENT","run_graph",{"instruction": req.instruction, "review": out.get("review",{}), "iter": out.get("iter", 0)}, provider=llm_provider)
    return out

@app.post("/agent/approve")
def approve(req: ApproveReq):
    RUN_APPROVALS[req.run_id] = bool(req.approve)
    return {"ok": True}

@app.post("/agent/send")
def send_email():
    # fetch last run from audit or keep in memory
    from .db import get_audit, add_audit
    run = next((l for l in get_audit() if l["actor"]=="AGENT" and l["action"]=="run_graph"), None)
    run_id = str(run["id"]) if run else "latest"
    if not run or not run["payload"]["review"]["passed"]:
        return {"ok": False, "error":"review not passed"}
    if not RUN_APPROVALS.get(run_id):
        return {"ok": False, "error":"not approved"}
    # here call the real mail sender; for now re-use draft payload
    add_audit("MAILER","send",{"run_id": run_id, "status":"SENT"})
    return {"ok": True, "status":"SENT", "run_id": run_id}