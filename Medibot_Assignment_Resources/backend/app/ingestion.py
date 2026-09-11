from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


ROLE_COLLECTIONS = {
    "doctor": ["general", "clinical", "nursing"],
    "nurse": ["general", "nursing"],
    "billing_executive": ["general", "billing"],
    "technician": ["general", "equipment"],
    "admin": ["general", "clinical", "nursing", "billing", "equipment"],
}


def _read_pdf_text(file_path: Path) -> str:
    if PdfReader is None:
        return ""
    reader = PdfReader(str(file_path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages)


def _read_markdown_text(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore")


def _normalise_heading(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _chunk_text(text: str, max_chars: int = 1200) -> list[str]:
    if not text:
        return []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        if current_len + len(line) > max_chars and current:
            chunks.append("\n".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line)
    if current:
        chunks.append("\n".join(current))
    return chunks


def build_document_index(base_dir: Path) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    collection_dirs = [
        ("general", base_dir / "general"),
        ("clinical", base_dir / "clinical"),
        ("nursing", base_dir / "nursing"),
        ("billing", base_dir / "billing"),
        ("equipment", base_dir / "equipment"),
    ]

    for collection_name, collection_dir in collection_dirs:
        if not collection_dir.exists():
            continue
        for file_path in sorted(collection_dir.iterdir()):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() == ".md":
                text = _read_markdown_text(file_path)
            elif file_path.suffix.lower() == ".pdf":
                text = _read_pdf_text(file_path)
            else:
                continue

            heading = file_path.stem.replace("_", " ").title()
            sections = text.splitlines()
            if not sections:
                continue

            for idx, chunk_text in enumerate(_chunk_text(text, max_chars=1000)):
                docs.append(
                    {
                        "id": f"{collection_name}:{file_path.name}:{idx}",
                        "source_document": file_path.name,
                        "collection": collection_name,
                        "access_roles": list(ROLE_COLLECTIONS.keys()),
                        "section_title": _normalise_heading(heading),
                        "chunk_type": "text",
                        "text": f"{heading}\n{chunk_text}",
                        "content": chunk_text,
                    }
                )

    for doc in docs:
        doc["access_roles"] = [
            role for role, collections in ROLE_COLLECTIONS.items() if doc["collection"] in collections
        ]
    return docs
