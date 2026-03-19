"""
doc_analyzer.py — Documentation ingestion and analysis using LlamaIndex.

What it does:
1. Walks the repo looking for documentation files (*.md, *.rst, *.txt, *.pdf)
2. Loads them with LlamaIndex's SimpleDirectoryReader
3. Builds a VectorStoreIndex for semantic querying
4. Returns a summary of the documentation as a string

Why LlamaIndex?
- Handles multiple file types with one reader
- Built-in text splitting handles large doc files
- Simple in-memory vector store — no external DB needed for MVP
"""
import os
from pathlib import Path
from typing import Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
    from llama_index.core.node_parser import SentenceSplitter
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    logger.warning("llama-index not installed — doc analysis will use fallback")


# File extensions we consider "documentation"
DOC_EXTENSIONS = {".md", ".rst", ".txt", ".pdf", ".adoc"}

# Max chars to return from the doc summary (prevents context overflow)
MAX_SUMMARY_CHARS = 8_000


def find_doc_files(repo_path: str) -> list[str]:
    """
    Walk the repo and return paths to all documentation files.
    Ignores hidden directories (.git, .venv, node_modules, etc.)
    """
    doc_files = []
    skip_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".tox"}

    for root, dirs, files in os.walk(repo_path):
        # Skip hidden/build directories in-place
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]

        for fname in files:
            if Path(fname).suffix.lower() in DOC_EXTENSIONS:
                doc_files.append(os.path.join(root, fname))

    logger.info(f"Found {len(doc_files)} documentation files in {repo_path}")
    return doc_files


def analyze_docs_simple(repo_path: str) -> str:
    """
    Fallback doc analyzer when LlamaIndex is not available.
    Just reads and concatenates doc file contents.
    """
    doc_files = find_doc_files(repo_path)
    if not doc_files:
        return "No documentation files found in the repository."

    parts = []
    total_chars = 0

    for fpath in doc_files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            rel_path = os.path.relpath(fpath, repo_path)
            chunk = f"\n\n--- {rel_path} ---\n{content}"

            if total_chars + len(chunk) > MAX_SUMMARY_CHARS:
                remaining = MAX_SUMMARY_CHARS - total_chars
                parts.append(chunk[:remaining] + "\n[... truncated ...]")
                break

            parts.append(chunk)
            total_chars += len(chunk)
        except Exception as e:
            logger.warning(f"Could not read {fpath}: {e}")

    return "\n".join(parts) if parts else "No readable documentation found."


async def analyze_docs(db: AsyncSession, repo_path: str, query: Optional[str] = None) -> str:
    """
    Analyze documentation files in the repo.

    If LlamaIndex is available, builds a vector index and queries it.
    Otherwise falls back to simple concatenation.

    Args:
        db: Async database session for token tracking
        repo_path: Absolute path to the repository root
        query: Optional query for semantic search. If None, returns full summary.

    Returns:
        A string containing the documentation analysis
    """
    if not os.path.isdir(repo_path):
        raise ValueError(f"repo_path is not a valid directory: {repo_path}")

    if not LLAMA_AVAILABLE:
        logger.info("Using fallback doc analyzer (LlamaIndex not installed)")
        return analyze_docs_simple(repo_path)

    doc_files = find_doc_files(repo_path)

    if not doc_files:
        return "No documentation files found in the repository."

    try:
        from app.api_manager.llm_adapters import LlamaIndexRotatorLLM
        from app.config import settings

        # Configure rotated LLM for LlamaIndex
        Settings.llm = LlamaIndexRotatorLLM(
            db=db,
            provider=settings.default_llm_provider,
            model_name=settings.default_llm_model
        )

        # Load documents from doc files only (not the whole repo)
        reader = SimpleDirectoryReader(input_files=doc_files)
        documents = reader.load_data()
        logger.info(f"Loaded {len(documents)} document chunks")

        # Build in-memory vector index
        text_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        Settings.text_splitter = text_splitter
        index = VectorStoreIndex.from_documents(documents)

        # Query the index
        query_engine = index.as_query_engine(similarity_top_k=8)
        q = query or (
            "Summarize: 1) what this project does 2) its architecture "
            "3) target users 4) missing documentation gaps"
        )
        response = await query_engine.aquery(q)
        result = str(response)

        logger.info(f"Doc analysis complete: {len(result)} chars")
        return result[:MAX_SUMMARY_CHARS]

    except Exception as e:
        logger.error(f"LlamaIndex analysis failed: {e} — using fallback")
        return analyze_docs_simple(repo_path)
