# GitHub Copilot Prompt — Multi-Modal Contract Analysis Tool

> Paste this entire prompt into GitHub Copilot Chat (or Copilot Workspace) to scaffold the full project.

---

## MASTER PROMPT

```
You are a senior full-stack AI engineer. Build a production-ready
"Multi-Modal Contract Analysis Tool" — a system that accepts legal
contracts (PDF or DOCX), then runs four parallel AI agents to extract
key data points, identify and categorize clauses, assess risks, and
produce a structured summary. The agents run concurrently and their
outputs are merged into a final JSON/PDF report.

Follow every instruction below exactly. Generate all files, folder
structures, code, configs, and documentation described.
```

---

## 1. PROJECT OVERVIEW

```
Project name : contract-analysis-tool
Description  : Upload a PDF or DOCX contract → multi-agent LangGraph
               pipeline extracts clauses, risks, data points, and a
               summary in parallel → results compiled into a report.

Stack
  Backend  : Python 3.11, FastAPI, LangGraph, LangChain, Celery, Redis
  LLM      : OpenAI GPT-4o (primary) with Anthropic Claude as fallback
  OCR/Parse: PyMuPDF (fitz), python-docx, Tesseract OCR (pytesseract)
  Vector DB: Pinecone (cloud) or pgvector (self-hosted) for RAG
  Database : PostgreSQL (jobs, results), AWS S3 / local MinIO (files)
  Frontend : React 18 + TypeScript + Vite + Tailwind CSS
  Auth     : JWT via FastAPI-Users
  Testing  : pytest + httpx (backend), Vitest + React Testing Library
  Infra    : Docker Compose (dev), optional Kubernetes manifests
```

---

## 2. FOLDER STRUCTURE

```
Generate this exact folder and file structure:

contract-analysis-tool/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── config.py                # Pydantic Settings (env vars)
│   │   ├── dependencies.py          # DI: DB session, auth, S3
│   │   ├── routers/
│   │   │   ├── contracts.py         # POST /upload, GET /job/{id}
│   │   │   ├── reports.py           # GET /report/{id}, /export
│   │   │   └── auth.py              # login, register, refresh
│   │   ├── models/
│   │   │   ├── contract.py          # SQLAlchemy: Contract, Job, Report
│   │   │   └── user.py              # SQLAlchemy: User
│   │   ├── schemas/
│   │   │   ├── contract.py          # Pydantic I/O schemas
│   │   │   └── report.py
│   │   ├── services/
│   │   │   ├── parser.py            # PDF/DOCX → text + chunks
│   │   │   ├── ocr.py               # Tesseract OCR for scanned pages
│   │   │   ├── embedder.py          # OpenAI embeddings → vector store
│   │   │   └── report_compiler.py   # Merge agent outputs → report
│   │   ├── agents/
│   │   │   ├── base_agent.py        # Abstract BaseAgent class
│   │   │   ├── clause_agent.py      # Clause identification agent
│   │   │   ├── risk_agent.py        # Risk analysis agent
│   │   │   ├── extractor_agent.py   # Data extraction agent
│   │   │   ├── summary_agent.py     # Summarization agent
│   │   │   └── orchestrator.py      # LangGraph state graph + runner
│   │   ├── tasks/
│   │   │   └── celery_tasks.py      # Celery async task wrappers
│   │   ├── db/
│   │   │   ├── session.py           # SQLAlchemy async engine + session
│   │   │   └── migrations/          # Alembic migrations
│   │   └── utils/
│   │       ├── pdf_exporter.py      # reportlab → PDF report
│   │       └── logger.py            # Structured JSON logging
│   ├── tests/
│   │   ├── test_parser.py
│   │   ├── test_agents.py
│   │   ├── test_orchestrator.py
│   │   └── test_api.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── UploadZone.tsx       # Drag-and-drop file upload
│   │   │   ├── JobProgress.tsx      # Real-time SSE progress bar
│   │   │   ├── ClauseViewer.tsx     # Categorized clause list
│   │   │   ├── RiskPanel.tsx        # Risk cards with severity badges
│   │   │   ├── DataFields.tsx       # Extracted key-value pairs
│   │   │   └── ReportExport.tsx     # Download JSON / PDF buttons
│   │   ├── hooks/
│   │   │   ├── useUpload.ts
│   │   │   └── useJobStatus.ts      # SSE listener hook
│   │   ├── api/
│   │   │   └── client.ts            # Axios instance + typed endpoints
│   │   └── types/
│   │       └── index.ts             # Shared TypeScript interfaces
│   ├── Dockerfile
│   ├── vite.config.ts
│   └── package.json
├── docker-compose.yml
├── docker-compose.prod.yml
├── .github/
│   └── workflows/
│       └── ci.yml                   # GitHub Actions: lint + test
└── README.md
```

---

## 3. ENVIRONMENT VARIABLES

```
Generate backend/.env.example with ALL of these keys:

# LLM
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=gpt-4o
LLM_FALLBACK_MODEL=claude-sonnet-4-6
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/contracts
REDIS_URL=redis://redis:6379/0

# Storage
S3_BUCKET=contract-uploads
S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin

# Vector store
PINECONE_API_KEY=...
PINECONE_INDEX=contract-clauses
VECTOR_DIMENSION=1536

# Auth
SECRET_KEY=change-me-in-production
JWT_EXPIRE_MINUTES=60

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# OCR
TESSERACT_CMD=/usr/bin/tesseract
```

---

## 4. PARSING SERVICE

```
Generate backend/app/services/parser.py implementing:

class DocumentParser:
    """
    Converts PDF or DOCX files into clean text chunks suitable for LLM
    processing. Handles three document types:
      1. Native PDF (text-selectable) — use PyMuPDF (fitz) for fast
         text extraction preserving layout.
      2. Scanned PDF (image-only pages) — detect via empty text layer;
         rasterize each page at 300 DPI; pass to OCR service.
      3. DOCX — use python-docx to extract paragraphs and table cells
         in document order, preserving heading structure.

    After extraction, chunk text using LangChain's
    RecursiveCharacterTextSplitter with:
      chunk_size=1500, chunk_overlap=200,
      separators=["\n\n", "\n", ". ", " "]

    Return:
      ParseResult(
          raw_text: str,
          chunks: List[str],
          page_count: int,
          is_scanned: bool,
          metadata: dict   # filename, size, mime_type, page_count
      )
    """

Also generate backend/app/services/ocr.py:
    - Uses pytesseract with lang="eng" and config="--psm 6"
    - Preprocesses images with PIL: grayscale, threshold, deskew
    - Returns extracted text per page
```

---

## 5. AGENT IMPLEMENTATIONS

```
Generate ALL FOUR agents. Each must inherit from BaseAgent.

==== base_agent.py ====
from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

class BaseAgent(ABC):
    """
    Abstract base for all contract analysis agents.

    Every agent:
    - Initialises a primary LLM (GPT-4o) and fallback (Claude)
    - Uses structured output (JSON mode / response_format)
    - Retries up to 3 times on LLM error before switching to fallback
    - Logs input token count and output token count per call
    - Raises AgentError with context if both LLMs fail
    """
    def __init__(self, temperature: float = 0.1): ...

    @abstractmethod
    async def run(self, chunks: List[str], context: dict) -> dict: ...

    async def _call_llm(self, prompt: str, schema: dict) -> dict: ...


==== clause_agent.py ====
"""
Clause identification agent.

Prompt strategy: "chunk-then-label"
  1. For each text chunk, ask the LLM to identify all clause boundaries
     and assign each a clause_type from this controlled vocabulary:
       TERMINATION, LIABILITY, CONFIDENTIALITY, PAYMENT, INDEMNIFICATION,
       INTELLECTUAL_PROPERTY, GOVERNING_LAW, DISPUTE_RESOLUTION,
       FORCE_MAJEURE, WARRANTY, NON_COMPETE, ASSIGNMENT, RENEWAL,
       NOTICE, GENERAL (catch-all)
  2. Merge overlapping clause spans across chunks.
  3. Return list of Clause objects:
       {
         "clause_type": str,
         "text": str,          # verbatim clause text
         "page_hint": int,     # approximate page number
         "confidence": float   # 0.0–1.0
       }

System prompt (use exactly):
  You are a legal document analysis AI. Given a segment of a contract,
  identify and extract every distinct clause. For each clause:
  - Assign exactly one clause_type from the provided vocabulary.
  - Copy the clause text verbatim from the input.
  - Estimate confidence (0.0–1.0) based on how clearly the clause
    matches its type.
  Respond ONLY with a JSON array of clause objects. No preamble.
"""


==== risk_agent.py ====
"""
Risk analysis agent.

Prompt strategy: "clause-level risk scoring"
  Input: list of Clause objects from clause_agent output.
  For each clause, assess:
    - risk_level: LOW | MEDIUM | HIGH | CRITICAL
    - risk_category: LIABILITY | FINANCIAL | OPERATIONAL |
                     LEGAL_COMPLIANCE | REPUTATIONAL
    - risk_description: plain English explanation (≤2 sentences)
    - recommendation: suggested mitigation (≤1 sentence)

  Return list of RiskFlag objects:
    {
      "clause_type": str,
      "clause_text_snippet": str,  # first 120 chars
      "risk_level": str,
      "risk_category": str,
      "risk_description": str,
      "recommendation": str
    }

System prompt (use exactly):
  You are a contract risk analyst. For each clause provided, identify
  potential legal or business risks. Be specific about why each clause
  is risky — reference the clause's actual language. Assign risk_level
  as CRITICAL only for clauses with direct financial exposure > $1M,
  unlimited liability, or waived fundamental rights. Respond ONLY
  with a JSON array of RiskFlag objects. No preamble.
"""


==== extractor_agent.py ====
"""
Data extraction agent.

Prompt strategy: "targeted slot-filling"
  Uses a single structured prompt over the full document (first 8000
  tokens if document is very long) to fill all named slots.

  Required output schema (all fields, null if not found):
    {
      "parties": {
        "client":   { "name": str, "jurisdiction": str },
        "provider": { "name": str, "jurisdiction": str },
        "others":   []   # any additional named parties
      },
      "effective_date":    str | null,   # ISO 8601
      "expiration_date":   str | null,
      "auto_renewal":      bool | null,
      "renewal_notice_days": int | null,
      "contract_value":    str | null,   # preserve currency symbol
      "payment_terms":     str | null,
      "termination_notice_days": int | null,
      "liability_cap":     str | null,
      "governing_law":     str | null,
      "confidentiality_period": str | null,
      "ip_ownership":      str | null,
      "arbitration_required": bool | null
    }

System prompt (use exactly):
  You are a contract data extraction specialist. Extract all named
  fields from the contract text. For dates, output ISO 8601 format
  (YYYY-MM-DD). For monetary values, preserve the original currency
  and amount exactly as written. If a field is genuinely absent from
  the document, return null — do not guess. Respond ONLY with the
  JSON object matching the provided schema. No preamble.
"""


==== summary_agent.py ====
"""
Summarization agent.

Prompt strategy: "hierarchical summarization"
  Step 1: Summarize each chunk independently (map step).
  Step 2: Combine chunk summaries + extracted data into a final
          executive summary (reduce step).

  Output schema:
    {
      "executive_summary": str,   # 3–5 sentences, plain English
      "key_terms":         [str], # bullet-style key points, max 8
      "unusual_clauses":   [str], # clauses deviating from standard
      "overall_risk":      "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
      "recommended_actions": [str]  # top 3 action items for reviewer
    }

System prompt for map step:
  Summarize the following contract segment in 2–3 sentences. Focus on
  obligations, rights, and notable terms. Be concise and factual.

System prompt for reduce step:
  You are a senior contract attorney. Given the following partial
  summaries and extracted contract data, write an executive summary
  a business executive could read in under 30 seconds. Then list the
  8 most important contract terms, any unusual or non-standard clauses,
  and the top 3 recommended actions for the reviewing party.
  Respond ONLY with the JSON object. No preamble.
"""
```

---

## 6. ORCHESTRATOR (LANGGRAPH)

```
Generate backend/app/agents/orchestrator.py implementing a LangGraph
StateGraph that runs the four agents in parallel where possible.

State schema:
  class ContractState(TypedDict):
      job_id:        str
      chunks:        List[str]
      raw_text:      str
      metadata:      dict
      clauses:       List[dict]     # clause_agent output
      risks:         List[dict]     # risk_agent output
      extracted:     dict           # extractor_agent output
      summary:       dict           # summary_agent output
      report:        dict           # final merged report
      errors:        List[str]
      status:        str            # PENDING|RUNNING|COMPLETE|FAILED

Graph topology:
  START
    │
    ▼
  [parse_node]        → runs DocumentParser, populates chunks + raw_text
    │
    ├──────────────────────────────────────────┐
    ▼                                          ▼
  [clause_node]                         [extractor_node]
  (clause_agent.run)                    (extractor_agent.run)
    │                                          │
    ▼                                          │
  [risk_node]                                  │
  (risk_agent.run,                             │
   needs clause_node output)                   │
    │                                          │
    └──────────┬───────────────────────────────┘
               ▼
          [summary_node]
          (summary_agent.run,
           needs all above outputs)
               │
               ▼
          [compile_node]
          (report_compiler.compile)
               │
               ▼
             END

Use asyncio.gather() inside each node for internal parallelism.
Implement a progress_callback(job_id, step, pct) that writes to Redis
so the frontend SSE endpoint can stream progress updates.

Error handling: if any node fails, catch the exception, append to
state.errors, and continue with partial results — do not abort the
entire graph. Mark the report with "partial": true if any agent failed.
```

---

## 7. FASTAPI ROUTES

```
Generate backend/app/routers/contracts.py with these endpoints:

POST /api/v1/contracts/upload
  - Accept multipart/form-data with file: UploadFile
  - Validate: PDF or DOCX only, max 50 MB
  - Save raw file to S3/MinIO
  - Create Job record in PostgreSQL (status=PENDING)
  - Enqueue Celery task: analyze_contract.delay(job_id, s3_key)
  - Return: { "job_id": str, "status": "PENDING" }

GET /api/v1/contracts/job/{job_id}
  - Return current Job status + progress percentage
  - Return: { "job_id", "status", "progress_pct", "created_at" }

GET /api/v1/contracts/job/{job_id}/stream
  - Server-Sent Events endpoint
  - Subscribe to Redis channel for job_id
  - Stream progress events: data: {"step": str, "pct": int}\n\n
  - On completion stream: data: {"status": "COMPLETE", "report_id": str}\n\n

GET /api/v1/reports/{report_id}
  - Return full report JSON
  - Include: clauses, risks, extracted, summary, metadata

GET /api/v1/reports/{report_id}/export?format=pdf|json
  - format=json: return report as downloadable JSON file
  - format=pdf:  generate PDF via reportlab, return as file download
```

---

## 8. CELERY TASK

```
Generate backend/app/tasks/celery_tasks.py:

@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def analyze_contract(self, job_id: str, s3_key: str):
    """
    Celery task that:
    1. Downloads file from S3/MinIO
    2. Calls DocumentParser.parse()
    3. Embeds chunks into vector store (for future RAG queries)
    4. Runs ContractOrchestrator.run(state) via asyncio.run()
    5. Saves final report to PostgreSQL
    6. Updates job status to COMPLETE or FAILED
    7. Publishes completion event to Redis pub/sub channel
    """

Celery config:
  - broker: Redis (CELERY_BROKER_URL)
  - result backend: Redis (CELERY_RESULT_BACKEND)
  - task_serializer: json
  - worker_concurrency: 4
  - task_time_limit: 300  # 5 min hard limit per job
```

---

## 9. FRONTEND COMPONENTS

```
Generate ALL frontend components with full TypeScript types.

==== types/index.ts ====
export interface Clause {
  clause_type: ClauseType;
  text: string;
  page_hint: number;
  confidence: number;
}

export type ClauseType =
  | "TERMINATION" | "LIABILITY" | "CONFIDENTIALITY" | "PAYMENT"
  | "INDEMNIFICATION" | "INTELLECTUAL_PROPERTY" | "GOVERNING_LAW"
  | "DISPUTE_RESOLUTION" | "FORCE_MAJEURE" | "WARRANTY"
  | "NON_COMPETE" | "ASSIGNMENT" | "RENEWAL" | "NOTICE" | "GENERAL";

export interface RiskFlag {
  clause_type: string;
  clause_text_snippet: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_category: string;
  risk_description: string;
  recommendation: string;
}

export interface ExtractedData {
  parties: { client: Party; provider: Party; others: Party[] };
  effective_date: string | null;
  expiration_date: string | null;
  auto_renewal: boolean | null;
  contract_value: string | null;
  payment_terms: string | null;
  termination_notice_days: number | null;
  liability_cap: string | null;
  governing_law: string | null;
}

export interface Summary {
  executive_summary: string;
  key_terms: string[];
  unusual_clauses: string[];
  overall_risk: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  recommended_actions: string[];
}

export interface Report {
  report_id: string;
  job_id: string;
  clauses: Clause[];
  risks: RiskFlag[];
  extracted: ExtractedData;
  summary: Summary;
  metadata: Record<string, unknown>;
  partial: boolean;
  created_at: string;
}


==== components/UploadZone.tsx ====
- Drag-and-drop zone using HTML5 drag events + file input fallback
- Show file name, size, and type after selection
- Validate PDF/DOCX client-side before upload
- On submit: call POST /api/v1/contracts/upload
- On success: store job_id and navigate to progress view
- Show upload progress bar via axios onUploadProgress

==== components/JobProgress.tsx ====
- Accept job_id prop
- Use useJobStatus hook to listen to SSE stream
- Show animated progress bar (0–100%)
- Show current step label (Parsing, Extracting, Analyzing risks, etc.)
- On COMPLETE: navigate to report view with report_id

==== hooks/useJobStatus.ts ====
- Opens EventSource to GET /api/v1/contracts/job/{job_id}/stream
- Parses SSE events into { step, pct, status, report_id }
- Returns { progress, step, status, reportId, error }
- Closes EventSource on unmount or when status === COMPLETE

==== components/ClauseViewer.tsx ====
- Group clauses by clause_type
- Render each group as an expandable accordion section
- Color-code clause types (use Tailwind: indigo for TERMINATION,
  red for LIABILITY, yellow for PAYMENT, green for IP, etc.)
- Show confidence badge on each clause card
- Search/filter input to search clause text

==== components/RiskPanel.tsx ====
- Sort risks by severity: CRITICAL > HIGH > MEDIUM > LOW
- Render each as a card with colored left border
- CRITICAL = red, HIGH = orange, MEDIUM = yellow, LOW = gray
- Show risk_description and recommendation on expand
- Summary bar at top showing count per severity level

==== components/DataFields.tsx ====
- Render extracted data as labeled key-value grid
- Show "Not found" in muted text for null values
- Highlight auto_renewal: true with amber badge
- Format dates as "Jan 15, 2025" (human readable)

==== components/ReportExport.tsx ====
- Two buttons: Download JSON, Download PDF
- Call GET /api/v1/reports/{id}/export?format=json|pdf
- Trigger browser download via blob URL
```

---

## 10. DOCKER COMPOSE

```
Generate docker-compose.yml with ALL of these services:

services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [db, redis, minio]
    env_file: backend/.env

  celery_worker:
    build: ./backend
    command: celery -A app.tasks.celery_tasks worker --loglevel=info
    depends_on: [db, redis, minio]
    env_file: backend/.env

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    depends_on: [backend]

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: contracts
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes: [pgdata:/var/lib/postgresql/data]
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports: ["9000:9000", "9001:9001"]
    volumes: [miniodata:/data]

volumes:
  pgdata:
  miniodata:
```

---

## 11. TESTING

```
Generate tests for:

backend/tests/test_parser.py
  - test_parse_native_pdf(): use a 2-page sample PDF fixture
  - test_parse_scanned_pdf(): mock OCR output
  - test_parse_docx(): use a sample DOCX fixture
  - test_chunk_size(): assert all chunks <= 1500 chars

backend/tests/test_agents.py
  - Mock the LLM (use langchain's FakeListLLM or patch OpenAI)
  - test_clause_agent_returns_valid_schema()
  - test_risk_agent_scores_liability_high()
  - test_extractor_agent_finds_parties()
  - test_summary_agent_returns_executive_summary()
  - test_agent_fallback_to_claude_on_openai_error()

backend/tests/test_orchestrator.py
  - test_full_pipeline_completes(): end-to-end with mocked LLM
  - test_partial_result_on_agent_failure(): kill one agent, check partial=true
  - test_progress_events_published_to_redis()

backend/tests/test_api.py
  - test_upload_pdf_returns_job_id()
  - test_upload_invalid_type_returns_422()
  - test_get_job_status()
  - test_get_report_after_completion()
  - test_export_json()
  - test_export_pdf()

Use pytest-asyncio for all async tests.
Use pytest fixtures for DB session (use SQLite for tests), Redis mock,
and S3 mock (moto library).
```

---

## 12. README

```
Generate a complete README.md covering:

1. Project description and feature list
2. Architecture diagram reference (link to /docs/architecture.png)
3. Tech stack table
4. Prerequisites (Python 3.11, Node 20, Docker, Tesseract)
5. Local development setup (step-by-step)
6. Environment variables guide
7. Running tests
8. API reference (all endpoints with request/response examples)
9. Prompt strategy explanation for each agent
10. How to add a new agent
11. How to swap LLM providers
12. Deployment notes (Docker Compose prod, environment hardening)
13. Known limitations and future improvements
```

---

## 13. DESIGN DECISIONS & RATIONALE

```
Document these decisions as inline comments and in README:

LangGraph (not LangChain LCEL Chains):
  Reason: native parallel node execution, explicit state management,
  built-in retry/error handling per node, easier to add new agents
  without refactoring the entire pipeline.

Celery + Redis (not background tasks in FastAPI):
  Reason: contracts can take 30–90 seconds to process; Celery lets
  us scale workers independently, retry failed jobs, and gives durable
  task state that survives server restart.

Chunked prompting (not full-document in one prompt):
  Reason: contracts are often 20–80 pages; GPT-4o context window
  handles ~128K tokens but cost and latency grow linearly. Chunking
  at 1500 tokens with 200-token overlap keeps cost predictable while
  preserving clause context across boundaries.

Vector store (for future RAG):
  Reason: users will want to query "find all contracts with unlimited
  liability" across their contract library. Embedding chunks now
  enables this without re-processing.

Structured JSON output (response_format={"type":"json_object"}):
  Reason: eliminates prompt-variation risk in parsing LLM responses.
  Combined with Pydantic validation on the returned JSON, any schema
  violation is caught immediately and triggers a retry.

Fallback LLM (Claude after GPT-4o failure):
  Reason: production resilience. Both models support JSON mode and
  have similar legal-text comprehension. Fallback adds <500ms latency
  but prevents total failure during OpenAI outages.
```

---

## 14. COPILOT FOLLOW-UP PROMPTS

Use these follow-up prompts after the initial scaffold:

```
# Add Pinecone integration
Add backend/app/services/embedder.py that embeds all document chunks
using text-embedding-3-small and upserts them to Pinecone index
"contract-clauses" with metadata: {job_id, chunk_index, clause_type}.

# Add PDF export
Generate backend/app/utils/pdf_exporter.py using reportlab that takes
a Report dict and produces a multi-page PDF with: cover page (contract
name, date, overall risk level), executive summary page, clause table,
risk table sorted by severity, and raw extracted data appendix.

# Add clause similarity search
Add GET /api/v1/contracts/search?q=... that embeds the query, searches
Pinecone, and returns the top-5 matching clause snippets with their
source job_id and clause_type.

# Add authentication
Integrate FastAPI-Users with JWT tokens. Add user registration, login,
and token refresh endpoints. Protect all /api/v1/contracts/* and
/api/v1/reports/* routes with Depends(current_active_user).

# Add GitHub Actions CI
Generate .github/workflows/ci.yml that:
  - Runs on push to main and all PRs
  - Spins up postgres and redis services
  - Runs pytest with coverage (fail below 80%)
  - Runs eslint + vitest on frontend
  - Builds Docker images to verify they build successfully
```

---

*End of prompt. Paste this entire file into GitHub Copilot Chat and press Enter.*
