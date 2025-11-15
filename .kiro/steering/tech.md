---
inclusion: always
---

# Tech Stack

## Core Framework
- **FastAPI**: Web framework for API endpoints
- **Python 3.11**: Runtime environment
- **Uvicorn**: ASGI server

## Database & Storage
- **PostgreSQL 16**: Primary database with pgvector extension
- **SQLite3**: Local audit log and document storage (`data/copilot.sqlite3`)
- **pgvector**: Vector similarity search for embeddings
- Fallback to keyword search when `EMBEDDINGS_OFFLINE=1`

## AI/ML Libraries
- **LangGraph 0.2.35**: Agent orchestration and state management
- **sentence-transformers 3.2.1**: Local embeddings (384-dim vectors)
- **ragas 0.1.9**: RAG evaluation framework

## Key Dependencies
- **Pydantic 2.9.2**: Data validation and settings
- **SQLAlchemy 2.0.36**: Database ORM
- **Jinja2 3.1.4**: Template rendering

## Environment Variables
- `PG_URL`: PostgreSQL connection string (default: `postgresql+psycopg2://regops:regops@db:5432/regops`)
- `EMBEDDINGS_OFFLINE`: Set to "1" to disable vector embeddings and use keyword search
- `COPILOT_DB`: SQLite database path (default: `data/copilot.sqlite3`)

## Common Commands

### Docker (Recommended)
```bash
# Start services
docker compose up --build -d

# Enable pgvector extension
docker compose exec db psql -U regops -d regops -c 'CREATE EXTENSION IF NOT EXISTS vector;'

# View logs
docker compose logs -f api

# Stop services
docker compose down
```

### Local Development
```bash
# Install dependencies
make install

# Run dev server (with reload)
make run

# Run tests
make test

# Ingest sample SOP
make ingest

# Demo agent run
make demo
```

### API Endpoints
```bash
# Ingest SOP document
curl -F "file=@data/sops/sample_sop.txt" http://localhost:8000/ingest

# RAG query
curl -X POST http://localhost:8000/ask_rag \
  -H "Content-Type: application/json" \
  -d '{"question":"required email content for stability pulls"}'

# Run agent
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"instruction":"prepare stability pull list for week 12"}'

# View metrics
curl http://localhost:8000/metrics/summary

# View audit logs
curl http://localhost:8000/audit/logs

# Evaluate RAG
curl -X POST http://localhost:8000/eval/rag \
  -H "Content-Type: application/json" \
  -d '{"cases":[{"question":"...","ground":"..."}]}'
```

### UI Console
Access at `http://localhost:8000/app/` when server is running.

## Build & Deployment
- **Dockerfile**: Python 3.11-slim base, installs requirements, copies backend and data
- **docker-compose.yml**: Orchestrates API service and PostgreSQL with pgvector
- Port 8000 for API, port 5432 for database
