from ragas.metrics import context_precision, faithfulness
from ragas import EvaluationDataset, evaluate
from ..rag.pgstore import search

def eval_rag(cases):
    # cases: [{"question":...,"ground": "..."}]
    ds = EvaluationDataset.from_list([{
        "question": c["question"],
        "contexts": [h["text"] for h in search(c["question"], k=5)],
        "answer": "",               # model answer not required for ctx metrics
        "ground_truth": c["ground"]
    } for c in cases])
    res = evaluate(ds, metrics=[context_precision, faithfulness])
    return {m.name: float(res[m].mean()) for m in res}
