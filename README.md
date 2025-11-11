# RegOps Copilot (MVP)

Agentic QA/QC assistant for **stability pull** workflows. Runs **offline**. No LLM or API keys.

- Deterministic **Plan → Act → Review → Replan** loop
- Naive **RAG** over ingested SOPs (pgvector or keyword fallback)
- Stub tool calls for **LIMS**, **Sheets**, **Jira**, **Mailer**
- **Audit log** + **metrics** + static console at `/app`

---

## 1) Problem this solves

Stability pulls are repetitive and compliance-sensitive. Typical steps:

1. Get the week’s **pull list** from LIMS.
2. Add rows to a **tracker** (Sheets).
3. Open a **ticket** (Jira).
4. Draft a **QA email** with the table and **citations to SOPs**.
5. Verify **window (+/-3 days)**, **two-person review**, and **required fields** before sending.

This MVP automates steps 1–4 and blocks step 5 if checks fail. Everything is logged.

---

## 2) How it works (high level)

1. **Ingest SOP** → chunk → store in Postgres (`sop_chunks`).
2. **RAG** → retrieve top-k chunks for grounding and email citations.
3. **Agent loop**
   - **Plan**: parse week from instruction and build a tool plan.
   - **Act**: execute tools; carry forward context (e.g., table rows).
   - **Review**: rule checks (citations present, window, two-person, fields).
   - **Replan**: on any failure, iterate up to a cap.
4. **Audit/Metrics**: every step and result is stored and summarized.

> LIMS here is a **stub**; real systems would replace tool functions with live integrations.

---



- **RAG store**: Postgres table `sop_chunks(doc_name, chunk_no, text, embedding VECTOR(384)?).`
- If `pgvector` is missing, fallback to **keyword** search via `EMBEDDINGS_OFFLINE=1`.

---

## 4) Quick start

### Docker (recommended)
```bash
docker compose up --build -d
docker compose exec db psql -U regops -d regops -c 'CREATE EXTENSION IF NOT EXISTS vector;'
# UI console: http://localhost:8000/app/


# 1) Ingest SOP (plain text file)
curl -F "file=@data/sops/sample_sop.txt" http://localhost:8000/ingest

# 2) Ask RAG
curl -X POST http://localhost:8000/ask_rag -H "Content-Type: application/json" \
  -d '{"question":"required email content for stability pulls"}'

# 3) Run agent (week parsed from text: "week 12", "2025-W45", etc.)
curl -X POST http://localhost:8000/agent/run -H "Content-Type: application/json" \
  -d '{"instruction":"prepare stability pull list for week 12"}'

# 4) Lightweight eval
curl -X POST http://localhost:8000/eval/rag -H "Content-Type: application/json" \
  -d '{"cases":[{"question":"required email content for stability pulls","ground":"Lot Batch Expiry Storage"}]}'

# 5) Metrics / Audit
curl http://localhost:8000/metrics/summary
curl http://localhost:8000/audit/logs
