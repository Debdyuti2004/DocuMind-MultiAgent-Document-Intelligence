# DocuMind architecture map

## Runtime

- `app/main.py` is the FastAPI entry point. It serves the dashboard and the existing REST routes.
- `app/models/schemas.py` defines the API request and response models; `app/models/state.py` carries a query through the agent workflow.
- `app/static/` contains the browser client. It calls the same FastAPI routes used by API clients.

## Document ingestion

`POST /upload` → `DocumentLoader` validates PDF, DOCX, TXT, CSV, or XLSX → `DocumentParser` extracts page text and tables → `HierarchicalChunker` creates source-linked chunks → `EmbeddingService` encodes chunks → `VectorStore` persists them in ChromaDB → `ClassifierAgent` classifies the extracted text → `DocumentRegistry` and a JSON summary persist metadata.

## Retrieval and agents

`POST /query` → `AgentOrchestrator` resolves session follow-ups through `MemoryService` → `PlannerAgent` detects intent → `RetrievalAgent` searches ChromaDB → financial, risk, or research agents run only when the orchestrator's conditions select them → reasoning and optional verification run → response agent produces the answer and citations. Agent logs are returned in `QueryResponse`.

## Other services

- `GET /documents/{id}/summary`, `/sources`, and `/analysis` expose stored summaries, indexed chunks, and extracted tables.
- `POST /compare` compares two registered documents through `DocumentService`.
- `app/tools/calculation_tools.py` contains deterministic arithmetic; `app/tools/web_tools.py` is the external research integration.
- `app/services/llm_service.py` selects Ollama, OpenAI-compatible, or deterministic rule-based generation. Provider fallback is logged.

## Storage and limits

- Metadata and summaries: `data/processed/`
- Uploaded and bundled demonstration files: `data/uploads/` and `data/sample_docs/`
- Embeddings/index: `data/chroma/`
- Supported upload formats: `.pdf`, `.docx`, `.txt`, `.csv`, `.xlsx`; maximum upload size is 50 MiB.

## Trust boundary

Extractive summary fields are based on parsed document text. Comparison metrics must be present in both documents before a numeric delta is calculated. Retrieved citations use the indexed document ID and page number. If source material is missing, the UI says so instead of manufacturing a page or value.
