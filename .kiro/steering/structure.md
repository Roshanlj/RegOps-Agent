---
inclusion: always
---

# Project Structure

## Root Level
- `backend/`: Main application code
- `data/`: SQLite database and SOP documents
- `docker-compose.yml`: Service orchestration
- `Dockerfile`: Container build configuration
- `Makefile`: Development shortcuts
- `requirements.txt`: Python dependencies
- `README.md`: Project documentation

## Backend Organization

### `backend/app.py`
Main FastAPI application with all API endpoints:
- `/ingest`: Upload and process SOP documents
- `/ask`, `/ask_rag`: RAG query endpoints
- `/task`, `/agent/run`: Agent execution
- `/agent/approve`, `/agent/send`: Approval workflow
- `/audit/logs`: Audit trail access
- `/metrics/summary`: Performance metrics
- `/eval/rag`: RAG evaluation
- Static file serving at `/app`

### `backend/db.py`
SQLite database operations:
- `add_audit()`: Log all actions for compliance
- `get_audit()`: Retrieve audit logs
- `add_doc()`, `search_docs()`: Document management
- Tables: `docs`, `audit`

### `backend/agents/`
Agent orchestration components:
- `graph.py`: LangGraph state machine definition
- `planner.py`: Instruction parsing and plan generation
- `tool_exec.py`: Tool execution with context management
- `reviewer.py`: Compliance rule checking
- `toolspec.py`: Tool definitions and schemas
- `llm.py`: LLM interface (offline/local)

### `backend/rag/`
Retrieval-augmented generation:
- `pgstore.py`: PostgreSQL vector store operations
- `retriever.py`: RAG query logic with citations
- `sop_rules.py`: SOP-specific parsing rules
- `rag_eval.py`: RAG evaluation utilities

### `backend/tools/`
Integration stubs (replace with real implementations):
- `lims.py`: Laboratory Information Management System
- `sheets.py`: Google Sheets tracking
- `jira.py`: Ticket creation
- `mailer.py`: Email drafting and sending

### `backend/guards.py`
PII redaction and security:
- Regex-based PII detection (phone, email)
- `redact()` function for sanitizing outputs

### `backend/metrics.py`
Performance tracking:
- Agent run statistics
- Review pass/fail rates
- Tool failure counts

### `backend/static/`
Static web console files served at `/app`

### `backend/eval/`
Evaluation framework for testing RAG and agent quality

## Data Directory

### `data/copilot.sqlite3`
Local SQLite database for audit logs and document storage

### `data/sops/`
SOP documents for ingestion (plain text format)

## Architecture Patterns

### Agent Loop
1. **Plan**: Parse instruction, identify tools needed
2. **Act**: Execute tools sequentially with shared context
3. **Review**: Run compliance checks (citations, windows, fields)
4. **Replan**: Iterate on failures up to max iterations

### Context Flow
- Tools receive and update shared context dict
- Results from one tool available to subsequent tools via `context[step_id]`
- Context persists across agent loop iterations

### Audit Trail
- Every API call logs to `audit` table
- Includes timestamp, actor, action, and full payload
- Enables compliance review and debugging

### RAG Strategy
- Primary: pgvector similarity search on 384-dim embeddings
- Fallback: Keyword-based search in SQLite
- Always returns citations (doc_name, chunk_no)

## Code Conventions

### Error Handling
- Tools catch exceptions and return error dicts
- Agent continues execution, logs failures
- Review step blocks final action if critical checks fail

### Data Models
- Pydantic models for all API requests/responses
- Type hints throughout codebase
- Validation at API boundary

### Database Access
- Direct SQLite for audit/docs (simple, local)
- SQLAlchemy + psycopg2 for PostgreSQL (vector ops)
- No ORM models, raw SQL for simplicity

### Testing
- Evaluation endpoints for RAG quality
- Metrics endpoint for monitoring
- Audit logs for debugging
