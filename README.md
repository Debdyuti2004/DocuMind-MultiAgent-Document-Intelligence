# DocuMind — Multi-Agent Document Intelligence

DocuMind ingests documents, indexes their text in ChromaDB, answers questions with retrieved evidence, and routes work through a multi-agent workflow. The FastAPI backend also serves a responsive browser dashboard.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the route map, ingestion pipeline, retrieval/agent workflow, storage paths, and trust boundary.

## Features

- Upload and index PDF, DOCX, TXT, CSV, and XLSX files (up to 50 MiB).
- Search the document library; inspect extracted summaries, source chunks, and tables.
- Ask evidence-grounded questions over one or more documents.
- Inspect actual agent logs, verification results, confidence, calculations, and citations returned by the orchestrator.
- Compare documents using values found in both source texts; absent values remain unavailable.
- Dashboard summaries and query history are generated from backend responses and the current browser's local history.

## Requirements and setup

Python 3.10+ is recommended. A prepared Windows environment is included in `.venv`.

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/> for the dashboard, <http://127.0.0.1:8000/docs> for Swagger UI, and <http://127.0.0.1:8000/health> for service status. No separate Node/Vite server is needed; the existing FastAPI process serves `app/static/`.

If PowerShell blocks activation, invoke the environment directly:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Configuration

Settings load from environment variables or an optional `.env` file. Common options include `LLM_PROVIDER` (`ollama`, `openai`, or `mock`), `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `EMBEDDING_MODEL`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`, and `SIMILARITY_THRESHOLD`. Do not put API keys in browser code. The current query path uses extractive source matching and deterministic calculations; it does not invoke the configured LLM provider. OCR and external web research are unavailable in this build.

ChromaDB persists under `data/chroma/`. Parsed document metadata and summaries persist under `data/processed/`; uploads go to `data/uploads/`.

## How retrieval and agents work

Documents are parsed into pages/tables, split into source-linked chunks, embedded, and indexed in ChromaDB. A query is routed by rule-based planner logic, passed through hybrid retrieval, then conditionally through specialist agents, extractive evidence selection, exact-text/arithmetic verification, and response formatting. Financial calculations are derived from selected document text. Confidence is the fraction of claims/calculations that matched retrieved evidence and is not a calibrated probability. The response includes agent logs, extracted excerpts, calculations, citations, and this evidence-match score. Citation pages refer to the source chunk's extracted page metadata.

## Tests

```powershell
python -m pytest
```

The API's root endpoint returns JSON to API clients and the HTML workspace to browsers. Existing REST routes remain available.

## Demo

The repository includes sample PDFs in `data/sample_docs/`. Start the server, open the dashboard, upload a supported document, select it in **Ask DocuMind**, and ask a question. The **Compare** page requires two indexed documents. Queries and their returned agent logs are stored in the current browser's local history; backend session memory lasts for the server process lifetime.
