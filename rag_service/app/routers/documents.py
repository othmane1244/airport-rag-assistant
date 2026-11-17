"""Private document-management endpoints for the authenticated API service."""

import hashlib
import logging
import os
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from pypdf import PdfReader
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.rag.embeddings import get_embedder
from app.rag.pdf_loader import pdf_to_documents
from app.routers.query import get_chroma_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/documents", tags=["document administration"])

PDF_DIR = Path(__file__).resolve().parents[2] / "data" / "pdfs"
COLLECTION_NAME = "aga_documents"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 500


def _safe_filename(value: str | None) -> str:
    # Strip both POSIX and Windows path components, then reject hidden/control names.
    name = (value or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if (
        not name
        or name.startswith(".")
        or len(name) > 180
        or re.search(r"[\x00-\x1f\x7f]", name)
        or Path(name).suffix.casefold() != ".pdf"
    ):
        raise HTTPException(status_code=400, detail="Un fichier PDF avec un nom valide est requis.")
    return name


def _collection():
    return get_chroma_client().get_or_create_collection(COLLECTION_NAME)


def _source_records(collection) -> list[dict]:
    groups: dict[str, dict] = {}
    offset = 0
    page_size = 1000
    while True:
        records = collection.get(include=["metadatas"], limit=page_size, offset=offset)
        metadatas = records.get("metadatas") or []
        for metadata in metadatas:
            metadata = metadata or {}
            filename = metadata.get("source_file")
            if not filename:
                continue
            entry = groups.setdefault(
                filename,
                {
                    "filename": filename,
                    "chunks": 0,
                    "audience": metadata.get("audience", ""),
                    "managed_by_admin": metadata.get("managed_by") == "admin",
                },
            )
            entry["chunks"] += 1
            entry["managed_by_admin"] = entry["managed_by_admin"] or metadata.get("managed_by") == "admin"
        if len(metadatas) < page_size:
            break
        offset += page_size

    for entry in groups.values():
        path = PDF_DIR / entry["filename"]
        entry["stored"] = path.is_file() and path.resolve().parent == PDF_DIR.resolve()
        entry["size_bytes"] = path.stat().st_size if entry["stored"] else None
    return sorted(groups.values(), key=lambda item: item["filename"].casefold())


@router.get("")
def list_documents():
    """List indexed source PDFs and their chunk counts."""
    return {"documents": _source_records(_collection())}


async def _read_bounded_body(request: Request) -> bytes:
    parts = []
    size = 0
    async for part in request.stream():
        size += len(part)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Le PDF ne doit pas dépasser 20 Mo.")
        parts.append(part)
    return b"".join(parts)


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(filename: str, request: Request):
    """Accept a PDF body and keep extraction/embedding off the event loop."""
    payload = await _read_bounded_body(request)
    return await run_in_threadpool(_index_pdf, filename, payload)


def _index_pdf(raw_filename: str, payload: bytes):
    """Validate, extract, embed and index one PDF without calling paid OCR."""
    filename = _safe_filename(raw_filename)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    size = len(payload)
    if size <= 0 or size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Le PDF doit peser entre 1 octet et 20 Mo.")
    if not payload.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="Le fichier envoyé n'est pas un PDF valide.")

    final_path = PDF_DIR / filename
    if final_path.resolve().parent != PDF_DIR.resolve():
        raise HTTPException(status_code=400, detail="Nom de fichier invalide.")

    backup_path: Path | None = None
    new_ids: list[str] = []
    old_ids: set[str] = set()
    try:
        with tempfile.TemporaryDirectory(prefix=".aga-upload-", dir=PDF_DIR) as temp_dir:
            staged_path = Path(temp_dir) / filename
            staged_path.write_bytes(payload)

            try:
                reader = PdfReader(staged_path)
                page_count = len(reader.pages)
            except Exception as exc:
                raise HTTPException(status_code=415, detail="Impossible de lire ce PDF.") from exc
            if page_count == 0 or page_count > MAX_PDF_PAGES:
                raise HTTPException(status_code=422, detail="Le PDF doit contenir de 1 à 500 pages.")

            digest = hashlib.sha256(staged_path.read_bytes()).hexdigest()
            prefix = f"admin_{hashlib.sha256(filename.encode('utf-8')).hexdigest()[:12]}_{digest[:12]}"
            documents = pdf_to_documents(
                staged_path,
                doc_id_prefix=prefix,
                extra_metadata={"audience": "voyageur", "managed_by": "admin"},
                # Scanned PDFs need an explicitly configured OCR workflow; uploading
                # a file must never trigger an unexpected paid Mistral request.
                mistral_api_key="",
            )
            if not documents:
                raise HTTPException(
                    status_code=422,
                    detail="Aucun texte exploitable n'a été trouvé. Les PDF scannés doivent d'abord être OCRisés.",
                )
            for document in documents:
                document["metadata"]["source_file"] = filename

            embedder = get_embedder(
                settings.rag_offline_test_mode, settings.rag_local_files_only
            )
            vectors = embedder.embed([document["text"] for document in documents])
            collection = _collection()
            previous = collection.get(
                where={"source_file": filename}, include=["metadatas"]
            )
            old_ids = set(previous.get("ids") or [])
            new_ids = [document["id"] for document in documents]

            # Stage the file replacement. If indexing fails, restore the old PDF.
            if final_path.exists():
                backup_path = Path(temp_dir) / ".previous.pdf"
                os.replace(final_path, backup_path)
            os.replace(staged_path, final_path)

            try:
                collection.upsert(
                    ids=new_ids,
                    embeddings=vectors,
                    documents=[document["text"] for document in documents],
                    metadatas=[document["metadata"] for document in documents],
                )
                stale_ids = list(old_ids - set(new_ids))
                if stale_ids:
                    collection.delete(ids=stale_ids)
            except Exception:
                # New IDs are content-versioned, so old indexed chunks remain usable.
                created_ids = list(set(new_ids) - old_ids)
                if created_ids:
                    collection.delete(ids=created_ids)
                final_path.unlink(missing_ok=True)
                if backup_path and backup_path.exists():
                    os.replace(backup_path, final_path)
                raise

        return {
            "filename": filename,
            "chunks": len(documents),
            "pages": page_count,
            "replaced": bool(old_ids),
            "message": "Document indexé avec succès.",
        }
    except HTTPException:
        if backup_path and backup_path.exists() and not final_path.exists():
            os.replace(backup_path, final_path)
        raise
    except Exception as exc:
        if backup_path and backup_path.exists() and not final_path.exists():
            os.replace(backup_path, final_path)
        logger.exception("Document upload/indexing failed for %s", filename)
        raise HTTPException(status_code=500, detail="Échec de l'indexation du document.") from exc


@router.delete("")
def delete_document(filename: str):
    """Remove every indexed chunk and its stored PDF for one source file."""
    filename = _safe_filename(filename)
    collection = _collection()
    existing = collection.get(where={"source_file": filename}, include=["metadatas"])
    ids = existing.get("ids") or []
    if not ids:
        raise HTTPException(status_code=404, detail="Document introuvable dans l'index.")

    path = PDF_DIR / filename
    if path.resolve().parent != PDF_DIR.resolve():
        raise HTTPException(status_code=400, detail="Nom de fichier invalide.")

    backup_path = None
    try:
        if path.is_file():
            backup_path = PDF_DIR / f".{hashlib.sha256(filename.encode()).hexdigest()[:16]}.deleting"
            os.replace(path, backup_path)
        collection.delete(ids=ids)
        if backup_path:
            backup_path.unlink(missing_ok=True)
    except Exception as exc:
        if backup_path and backup_path.exists() and not path.exists():
            os.replace(backup_path, path)
        logger.exception("Document deletion failed for %s", filename)
        raise HTTPException(status_code=500, detail="Échec de la suppression du document.") from exc

    return {"filename": filename, "removed_chunks": len(ids), "message": "Document supprimé."}
