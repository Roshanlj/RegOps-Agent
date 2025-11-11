import json
from ..agents.graph import GRAPH

TESTS = [
  {"instruction":"prepare stability pull list for week 45",
   "must":[("review.passed", True), ("steps[0].result.items.__len__", 2)]}
]

def get(obj, path):
    for p in path.split("."):
        if p.endswith("]"):
            name, idx = p[:-1].split("["); obj = getattr(obj, name, obj[name]); obj = obj[int(idx)]
        else:
            obj = obj.get(p) if isinstance(obj, dict) else getattr(obj, p)
    return obj

def eval_tasks():
    results=[]
    for t in TESTS:
        out = GRAPH.invoke({"instruction": t["instruction"]})
        ok=True; fails=[]
        for k, v in t["must"]:
            # crude dotted accessor
            actual = eval(k, {}, {"review":out.get("review",{}), "steps":out.get("steps",[])})
            if actual != v: ok=False; fails.append((k, actual, v))
        results.append({"instruction": t["instruction"], "passed": ok, "fails": fails})
    return results
