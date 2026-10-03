"""Metadata extraction and document registry manager."""

import json
from pathlib import Path
from typing import Dict, List, Optional
from app.models.schemas import DocumentMetadata
from app.utils.config import settings
from app.utils.logging import logger


class DocumentRegistry:
    """Manages stored document metadata and processed state."""

    def __init__(self, registry_file: Path = settings.PROCESSED_DIR / "registry.json"):
        self.registry_file = registry_file
        self.registry: Dict[str, DocumentMetadata] = {}
        self._load()

    def _load(self) -> None:
        """Loads registry from disk."""
        if self.registry_file.exists():
            try:
                data = json.loads(self.registry_file.read_text(encoding="utf-8"))
                self.registry = {k: DocumentMetadata(**v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"Error loading registry: {e}")
                self.registry = {}

    def _save(self) -> None:
        """Persists registry to disk."""
        try:
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.model_dump() for k, v in self.registry.items()}
            self.registry_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Error saving registry: {e}")

    def register(self, meta: DocumentMetadata) -> None:
        """Registers or updates a document metadata entry."""
        self.registry[meta.document_id] = meta
        self._save()

    def get(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Retrieves document metadata by ID."""
        return self.registry.get(doc_id)

    def list_all(self) -> List[DocumentMetadata]:
        """Lists all registered documents."""
        return list(self.registry.values())

    def delete(self, doc_id: str) -> bool:
        """Removes a document from the registry."""
        if doc_id in self.registry:
            del self.registry[doc_id]
            self._save()
            return True
        return False


registry = DocumentRegistry()
