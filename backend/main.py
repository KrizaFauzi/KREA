"""KREA FastAPI app: a single streaming chat endpoint for the 3-part flow
(riset produk -> prompt video -> copy ke Gemini)."""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agents.orchestrator import stream_chat
from backend.config import settings

app = FastAPI(title="KREA", description="Riset produk TikTok -> prompt video")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Schemas -----------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


# --- Routes ------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": settings.model,
        "api_key_set": bool(settings.google_api_key),
        "rapidapi_set": bool(settings.rapidapi_key),
    }


@app.post("/chat")
def chat(req: ChatRequest) -> StreamingResponse:
    """Stream KREA's reply as NDJSON events (text deltas + video_prompt cards)."""
    generator = stream_chat(user_message=req.message, session_id=req.session_id)
    return StreamingResponse(generator, media_type="application/x-ndjson")
