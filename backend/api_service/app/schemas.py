"""
Schémas de données (Pydantic) pour l'endpoint /chat.
Définit le contrat structuré entre le frontend React et le backend FastAPI.
"""

from typing import Literal, Optional, List
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, max_length=2000, strip_whitespace=True, description="Message de l'utilisateur")
    lang: Optional[Literal["fr", "en", "ar"]] = Field(default="fr", description="Langue de communication")
    session_id: Optional[str] = Field(default=None, max_length=128, description="Identifiant de session")


# =========================
# CHAT RESPONSE
# =========================

class ChatResponse(BaseModel):
    type: Literal["text", "error"] = "text"
    reply: str
    lang: str = "fr"
    sources: List[str] = Field(default_factory=list)
    # Which component produced the reply (evaluation/debug): gemini, groq,
    # fallback_parking, fallback_excerpt, fallback_unavailable, no_result,
    # out_of_scope, flight_redirect, greeting.
    engine: Optional[str] = None
