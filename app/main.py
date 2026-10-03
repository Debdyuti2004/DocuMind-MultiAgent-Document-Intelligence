"""FastAPI application exposing REST endpoints for DocuMind Document Intelligence System."""

import json
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.document.metadata import registry
from app.document.loader import MAX_FILE_SIZE_BYTES, SUPPORTED_EXTENSIONS
from app.models.schemas import (
    CompareRequest,
    CompareResponse,
    DocumentMetadata,
    DocumentSummary,
    QueryRequest,
    QueryResponse,
)
from app.rag.vector_store import vector_store
from app.services.document_service import document_service
from app.agents.orchestrator import orchestrator
from app.utils.config import settings
from app.utils.logging import logger

app = FastAPI(
    title="DocuMind API",
    description="Multi-Agent Document Intelligence and Reasoning System API",
    version="1.0.0"
)

# The graphical dashboard is served by the same process as the API.
UI_DIR = Path(__file__).resolve().parent / "static"
app.mount("/ui", StaticFiles(directory=UI_DIR, html=True), name="ui")

# Allow the bundled same-origin UI and local Vite development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000", "http://localhost:8000",
        "http://127.0.0.1:5173", "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root(request: Request):
    # Browsers get the graphical workspace; API clients retain the status JSON.
    if "text/html" in request.headers.get("accept", ""):
        return HTMLResponse((UI_DIR / "index.html").read_text(encoding="utf-8"))
    return {
        "system": "DocuMind — Multi-Agent Document Intelligence",
        "status": "online",
        "version": "1.0.0",
        "indexed_chunks": vector_store.count(),
        "total_documents": len(registry.list_all())
    }


@app.get("/config")
def public_config():
    """Returns non-secret runtime settings needed by the dashboard."""
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.OLLAMA_MODEL if settings.LLM_PROVIDER == "ollama" else settings.OPENAI_MODEL if settings.LLM_PROVIDER == "openai" else "Rule-based fallback",
        "llm_invoked_by_query_pipeline": False,
        "embedding_model": settings.EMBEDDING_MODEL,
        "top_k": settings.TOP_K,
        "chunk_size": settings.CHUNK_SIZE,
        "chunk_overlap": settings.CHUNK_OVERLAP,
        "similarity_threshold": settings.SIMILARITY_THRESHOLD,
        "max_upload_bytes": MAX_FILE_SIZE_BYTES,
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        "ocr_available": False,
        "external_research_available": False,
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "vector_store_chunks": vector_store.count(),
        "registered_documents": len(registry.list_all())
    }


@app.post("/upload", response_model=Dict[str, Any])
async def upload_document(file: UploadFile = File(...)):
    """Uploads, validates, parses, indexes, classifies, and automatically summarizes a document."""
    file_path: Optional[Path] = None
    try:
        raw_filename = file.filename or ""
        safe_filename = Path(raw_filename.replace("\\", "/")).name
        if not safe_filename or safe_filename in {".", ".."}:
            raise HTTPException(status_code=400, detail="Please choose a valid filename.")
        if Path(safe_filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise HTTPException(status_code=415, detail=f"Unsupported file type. Supported types: {supported}.")

        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        stored_filename = safe_filename
        candidate = settings.UPLOAD_DIR / stored_filename
        if candidate.exists():
            stored_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
        file_path = (settings.UPLOAD_DIR / stored_filename).resolve()
        if file_path.parent != settings.UPLOAD_DIR.resolve():
            raise HTTPException(status_code=400, detail="Invalid filename.")

        total_bytes = 0
        with file_path.open("xb") as buffer:
            while chunk := await file.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(status_code=413, detail="The file exceeds the 50 MiB upload limit.")
                buffer.write(chunk)

        doc_meta, summary = document_service.ingest_document(file_path, original_filename=safe_filename)
        return {
            "status": "success",
            "metadata": doc_meta.model_dump(),
            "summary": summary.model_dump()
        }
    except HTTPException:
        if file_path and file_path.exists():
            file_path.unlink(missing_ok=True)
        raise
    except ValueError as e:
        if file_path and file_path.exists():
            file_path.unlink(missing_ok=True)
        logger.warning("Upload rejected: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        if file_path and file_path.exists():
            file_path.unlink(missing_ok=True)
        logger.exception("Document upload/processing failed")
        raise HTTPException(status_code=500, detail="Document processing failed. Check that the file is valid and contains readable content.")
    finally:
        await file.close()


@app.get("/documents", response_model=List[DocumentMetadata])
def list_documents():
    """Lists all registered documents."""
    return registry.list_all()


@app.get("/documents/{document_id}", response_model=DocumentMetadata)
def get_document(document_id: str):
    """Retrieves metadata for a specific document."""
    meta = registry.get(document_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Document not found")
    return meta


@app.delete("/documents/{document_id}")
def delete_document(document_id: str):
    """Deletes a document from the registry and vector database."""
    meta = registry.get(document_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Document not found")
    
    vector_store.delete_document(document_id)
    registry.delete(document_id)
    uploaded_path = (settings.UPLOAD_DIR / Path(meta.storage_filename or meta.filename).name).resolve()
    if uploaded_path.parent == settings.UPLOAD_DIR.resolve() and uploaded_path.exists():
        uploaded_path.unlink(missing_ok=True)
    (settings.PROCESSED_DIR / f"{document_id}_summary.json").unlink(missing_ok=True)
    return {"status": "deleted", "document_id": document_id}


@app.post("/query", response_model=QueryResponse)
def execute_query(req: QueryRequest):
    """Executes a natural language query through the dynamic multi-agent orchestrator."""
    start_t = time.perf_counter()
    try:
        if req.document_ids:
            missing = [document_id for document_id in req.document_ids if registry.get(document_id) is None]
            if missing:
                raise HTTPException(status_code=404, detail="One or more selected documents were not found.")
        state = orchestrator.process_query(
            query=req.query,
            document_ids=req.document_ids,
            session_id=req.session_id or "default_session",
            enable_research=req.enable_research,
            enable_verification=req.enable_verification
        )

        elapsed = time.perf_counter() - start_t

        return QueryResponse(
            query=state.query,
            answer=state.final_answer or "No answer synthesized.",
            document_ids=state.document_ids,
            intent=state.intent or "document_qa",
            plan=state.plan,
            explicit_facts=state.explicit_facts,
            derived_calculations=state.derived_calculations,
            interpretations=state.interpretations,
            external_research=state.external_research,
            verified_claims=state.verification_results,
            sources=state.sources,
            confidence=state.confidence_level,
            confidence_score=state.confidence_score,
            execution_time_seconds=round(elapsed, 3),
            agent_logs=state.agent_logs
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Query execution failed")
        raise HTTPException(status_code=500, detail="Query processing failed. Check the service configuration and try again.")


@app.post("/compare", response_model=CompareResponse)
def compare_documents(req: CompareRequest):
    """Performs side-by-side comparison between two documents."""
    try:
        return document_service.compare_documents(req.doc1_id, req.doc2_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Document comparison failed")
        raise HTTPException(status_code=500, detail="Document comparison failed.")


@app.get("/documents/{document_id}/summary", response_model=DocumentSummary)
def get_document_summary(document_id: str):
    """Fetches automatic executive summary and suggested questions for a document."""
    if not registry.get(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    summary_path = settings.PROCESSED_DIR / f"{document_id}_summary.json"
    data = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    if data.get("summary_version") != 2:
        chunks = vector_store.get_document_chunks(document_id)
        pages = [SimpleNamespace(text=chunk.get("text", ""), sections=[]) for chunk in chunks]
        metadata = registry.get(document_id)
        data = document_service.generate_document_summary(
            document_id, metadata.filename, metadata.document_type, pages, []
        ).model_dump()
        if not chunks:
            data["executive_summary"] = "No indexed source text is available for this document."
            data["key_facts"] = []
            data["important_findings"] = []
            data["potential_risks"] = []
    return DocumentSummary(**data)


@app.get("/documents/{document_id}/sources")
def get_document_sources(document_id: str):
    """Returns all indexed chunks for a document."""
    if not registry.get(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    chunks = vector_store.get_document_chunks(document_id)
    return {"document_id": document_id, "chunk_count": len(chunks), "chunks": chunks}


@app.get("/documents/{document_id}/analysis")
def get_document_analysis(document_id: str):
    """Returns extracted tables and values supported by indexed text."""
    if not registry.get(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    from app.tools.document_tools import extract_table_tool
    res = extract_table_tool.execute(document_id=document_id)
    from app.agents.financial_agent import financial_agent
    chunks = vector_store.get_document_chunks(document_id)
    extracted_metrics = financial_agent._extract_metrics("\n".join(chunk.get("text", "") for chunk in chunks))
    return {
        "document_id": document_id,
        "tables": res.data if res.success else [],
        "metrics": extracted_metrics,
        "table_extraction_available": res.success,
    }
