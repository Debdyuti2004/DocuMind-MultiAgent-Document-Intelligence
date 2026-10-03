"""Intelligent hierarchical chunker maintaining document lineage and citation metadata."""

import re
from typing import List
from app.document.parser import ParsedPage
from app.models.schemas import DocumentChunk
from app.utils.config import settings


class HierarchicalChunker:
    """Chunks documents hierarchically: Document -> Page -> Section -> Paragraphs -> Chunks."""

    def __init__(self, chunk_size: int = settings.CHUNK_SIZE, chunk_overlap: int = settings.CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc_id: str, filename: str, pages: List[ParsedPage]) -> List[DocumentChunk]:
        """Performs hierarchical chunking across all pages and sections of a document."""
        chunks: List[DocumentChunk] = []
        global_index = 0

        for page in pages:
            page_num = page.page_number

            for section in page.sections:
                heading = section.get("heading", "General")
                content = section.get("content", "").strip()

                if not content:
                    continue

                # Split content into paragraphs
                paragraphs = self._split_paragraphs(content)
                section_chunks = self._build_chunks_from_paragraphs(
                    paragraphs=paragraphs,
                    doc_id=doc_id,
                    filename=filename,
                    page=page_num,
                    section=heading,
                    start_index=global_index
                )

                chunks.extend(section_chunks)
                global_index += len(section_chunks)

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """Splits text into paragraphs by double newlines or punctuation groupings."""
        raw_paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not raw_paras:
            # Fallback to sentence groupings
            sentences = re.split(r"(?<=[.!?])\s+", text)
            return [s.strip() for s in sentences if s.strip()]
        return raw_paras

    def _build_chunks_from_paragraphs(
        self,
        paragraphs: List[str],
        doc_id: str,
        filename: str,
        page: int,
        section: str,
        start_index: int
    ) -> List[DocumentChunk]:
        """Assembles paragraphs into chunks adhering to target size and overlap."""
        chunks: List[DocumentChunk] = []
        current_chunk_paragraphs: List[str] = []
        current_length = 0
        local_chunk_idx = start_index

        for para in paragraphs:
            para_len = len(para)

            # If adding this paragraph exceeds target chunk size and we have text, flush chunk
            if current_length + para_len > self.chunk_size and current_chunk_paragraphs:
                chunk_text = " ".join(current_chunk_paragraphs).strip()
                chunks.append(
                    self._create_chunk_model(
                        doc_id=doc_id,
                        filename=filename,
                        page=page,
                        section=section,
                        text=chunk_text,
                        index=local_chunk_idx
                    )
                )
                local_chunk_idx += 1

                # Retain overlap from end of previous chunk if possible
                overlap_text = chunk_text[-self.chunk_overlap:] if len(chunk_text) > self.chunk_overlap else ""
                current_chunk_paragraphs = [overlap_text, para] if overlap_text else [para]
                current_length = sum(len(p) for p in current_chunk_paragraphs)
            else:
                current_chunk_paragraphs.append(para)
                current_length += para_len + 1

        if current_chunk_paragraphs:
            chunk_text = " ".join(current_chunk_paragraphs).strip()
            if chunk_text:
                chunks.append(
                    self._create_chunk_model(
                        doc_id=doc_id,
                        filename=filename,
                        page=page,
                        section=section,
                        text=chunk_text,
                        index=local_chunk_idx
                    )
                )

        return chunks

    def _create_chunk_model(
        self, doc_id: str, filename: str, page: int, section: str, text: str, index: int
    ) -> DocumentChunk:
        """Constructs a validated DocumentChunk schema instance."""
        token_est = len(text.split())
        return DocumentChunk(
            chunk_id=f"chk_{doc_id}_{page}_{index}",
            document_id=doc_id,
            filename=filename,
            page=page,
            section=section,
            text=text,
            chunk_index=index,
            token_count=token_est,
        )
