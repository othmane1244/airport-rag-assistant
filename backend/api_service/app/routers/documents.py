"""Authenticated proxy to the private RAG document-management endpoints."""

import logging

import requests
from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import require_document_admin
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/documents", tags=["document administration"])
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _rag_request(method: str, path: str, **kwargs):
    try:
        response = requests.request(
            method,
            f"{settings.rag_service_url.rstrip('/')}{path}",
            timeout=(5, 300),
            **kwargs,
        )
    except requests.RequestException as exc:
        logger.exception("RAG document-management request failed")
        raise HTTPException(status_code=503, detail="Knowledge service is unavailable") from exc

    if not response.ok:
        try:
            detail = response.json().get("detail", "Document operation failed")
        except ValueError:
            detail = "Document operation failed"
        raise HTTPException(status_code=response.status_code, detail=detail)
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Invalid response from knowledge service") from exc


@router.get("")
def list_documents(_user: dict = Depends(require_document_admin)):
    return _rag_request("GET", "/admin/documents")


async def _read_bounded_body(request: Request) -> bytes:
    parts = []
    size = 0
    async for part in request.stream():
        size += len(part)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Le PDF ne doit pas dépasser 20 Mo.")
        parts.append(part)
    return b"".join(parts)


@router.post("")
async def upload_document(
    request: Request,
    filename: str,
    _user: dict = Depends(require_document_admin),
):
    payload = await _read_bounded_body(request)
    return _rag_request(
        "POST",
        "/admin/documents",
        params={"filename": filename},
        data=payload,
        headers={"Content-Type": "application/pdf"},
    )


@router.delete("")
def delete_document(
    filename: str,
    _user: dict = Depends(require_document_admin),
):
    return _rag_request("DELETE", "/admin/documents", params={"filename": filename})
