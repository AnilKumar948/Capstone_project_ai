# Contract Analysis Tool

Production-oriented multi-modal contract analysis system. Upload a PDF or DOCX contract and run four AI agents in parallel to extract clauses, assess risk, capture structured data, and generate executive summaries with JSON/PDF outputs.

## Features
- PDF and DOCX upload with validation and storage in S3/MinIO
- OCR fallback for scanned PDFs (Tesseract)
- Four specialized AI agents coordinated by LangGraph
- Parallelized analysis pipeline with partial-failure tolerance
- Celery + Redis async processing and SSE job progress streaming
- JSON and PDF report export
- React + TypeScript frontend for upload, progress, and report review

## Architecture
Architecture diagram: /docs/architecture.png

## Tech Stack
| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, LangGraph, Celery, Redis |
| LLM | OpenAI GPT-4o primary, Anthropic Claude fallback |
| Parsing/OCR | PyMuPDF, python-docx, pytesseract |
| Vector | Pinecone-ready embedding service |
| DB | PostgreSQL (SQLAlchemy async) |
| Storage | S3/MinIO |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Testing | pytest, pytest-asyncio, httpx, Vitest |

## Prerequisites
- Python 3.11
- Node.js 20
- Docker + Docker Compose
- Tesseract OCR

## Local Development
1. Copy backend environment file:
   - cp backend/.env.example backend/.env
2. Start containers:
   - docker compose up --build
3. Backend API:
   - http://localhost:8000
4. Frontend app:
   - http://localhost:5173

### Without Docker
1. Backend:
   - cd backend
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\\Scripts\\activate)
   - pip install -r requirements.txt
   - uvicorn app.main:app --reload
2. Frontend:
   - cd frontend
   - npm install
   - npm run dev

## Environment Variables
See backend/.env.example for complete keys. Main groups:
- LLM: model selection, API keys, generation settings
- Database/Redis
- S3/MinIO credentials and endpoint
- Vector store metadata
- JWT auth settings
- Celery broker/result backend
- Tesseract executable path

## Running Tests
- Backend:
  - cd backend
  - pytest
- Frontend:
  - cd frontend
  - npm run test

## API Reference
### Upload Contract
POST /api/v1/contracts/upload
- multipart/form-data: file
- response:
```json
{ "job_id": "uuid", "status": "PENDING" }
```

### Job Status
GET /api/v1/contracts/job/{job_id}
- response:
```json
{ "job_id": "uuid", "status": "RUNNING", "progress_pct": 65, "created_at": "..." }
```

### Job Progress Stream (SSE)
GET /api/v1/contracts/job/{job_id}/stream
- events:
```text
data: {"step":"Parsing","pct":20}

data: {"status":"COMPLETE","report_id":"uuid"}
```

### Get Report
GET /api/v1/reports/{report_id}
- returns clauses, risks, extracted, summary, metadata, partial

### Export Report
GET /api/v1/reports/{report_id}/export?format=pdf|json
- json: downloadable JSON
- pdf: downloadable PDF

## Agent Prompt Strategy
- Clause Agent: chunk-then-label classification with fixed clause vocabulary
- Risk Agent: clause-level risk scoring across severity and category
- Extractor Agent: targeted slot-filling with null for absent fields
- Summary Agent: hierarchical map-reduce summarization

## Add A New Agent
1. Create new class in backend/app/agents inheriting BaseAgent.
2. Define strict JSON schema and system prompt.
3. Add orchestrator node and edges in backend/app/agents/orchestrator.py.
4. Extend report compiler and frontend types/components if needed.
5. Add tests for schema, failure handling, and orchestration.

## Swap LLM Providers
- Update provider classes in backend/app/agents/base_agent.py.
- Keep structured JSON response contract unchanged.
- Update config keys in backend/app/config.py and backend/.env.example.
- Extend fallback chain and retry behavior tests.

## Deployment Notes
- Use docker-compose.prod.yml for production-like deployment.
- Enforce strong secrets for JWT and API keys.
- Restrict CORS, apply TLS termination, and isolate Redis/PostgreSQL networking.
- Enable DB backups and object storage lifecycle policies.
- Add observability: structured logs, metrics, and alerting.

## Design Decisions and Rationale
- LangGraph over LCEL chains:
  - Native parallel branches, explicit state transitions, and easier node-level retries.
- Celery + Redis over FastAPI background tasks:
  - Durable task handling for long-running 30-90 second workloads and horizontal worker scaling.
- Chunked prompting over full-document prompting:
  - Predictable cost/latency on long contracts while preserving context with overlap.
- Vector indexing during ingest:
  - Enables cross-contract semantic retrieval without reprocessing files later.
- Structured JSON output:
  - Reduces parser fragility and supports strict schema validation + retries.
- Claude fallback after GPT-4o failure:
  - Increases production resiliency during provider outages with minimal latency overhead.

## Known Limitations
- Auth routes are scaffolded and should be replaced with full FastAPI-Users integration.
- Embedder is Pinecone-ready but currently stubbed for offline-friendly scaffolding.
- PDF export layout is functional but should be expanded for richer tables/branding.
- Alembic migrations are placeholder-only and need generated revisions.

## Future Improvements
- Full Pinecone upsert/query endpoints
- Contract library search UI
- Rich PDF formatting and templates
- Role-based access control and audit logs
- Kubernetes manifests and autoscaling policies
