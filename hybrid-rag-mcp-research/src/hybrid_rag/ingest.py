from __future__ import annotations

from pathlib import Path

from .models import Document

SUPPORTED_SUFFIXES = {".md", ".txt"}


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    """Split text into overlapping character windows without emitting empty chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap
    while start < len(normalized):
        piece = normalized[start : start + chunk_size].strip()
        if piece:
            chunks.append(piece)
        if start + chunk_size >= len(normalized):
            break
        start += step
    return chunks


def load_documents(
    corpus_dir: str | Path,
    chunk_size: int = 1800,
    overlap: int = 120,
) -> list[Document]:
    """Load Markdown and text files recursively into stable document chunks."""
    root = Path(corpus_dir).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Corpus directory does not exist: {root}")

    documents: list[Document] = []
    paths = sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    )
    for path in paths:
        content = path.read_text(encoding="utf-8")
        relative_source = path.relative_to(root).as_posix()
        for index, chunk in enumerate(chunk_text(content, chunk_size, overlap)):
            doc_id = f"{relative_source}#{index}"
            documents.append(
                Document(
                    doc_id=doc_id,
                    text=chunk,
                    metadata={
                        "source": relative_source,
                        "chunk_index": index,
                        "file_type": path.suffix.lower().lstrip("."),
                    },
                )
            )

    if not documents:
        raise ValueError(f"No Markdown or text files found in corpus: {root}")
    return documents
