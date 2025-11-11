.PHONY: install run test ingest demo

install:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

run:
	. .venv/bin/activate && uvicorn backend.app:app --reload --port 8000

test:
	. .venv/bin/activate && pytest -q

ingest:
	curl -F "file=@data/sops/sample_sop.txt" http://localhost:8000/ingest

demo:
	curl -X POST http://localhost:8000/task -H "Content-Type: application/json" -d '{"instruction":"prepare stability pull list for week 45"}'
