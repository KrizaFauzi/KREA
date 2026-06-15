"""Orchestrator — the main agent loop (Google Gemma 4 31B via google-genai).

KREA runs ONE session with three parts:
  1. Riset Produk  — research a niche the user wants using live TikTok data
     (tool `search_tiktok`) plus brainstorming, and recommend product angles.
  2. Prompt Video  — once the user picks a product, produce a ready-to-paste
     video-generation prompt (tool `make_video_prompt`).
  3. Copy ke Gemini — KREA does NOT generate the video; it tells the user to
     paste the prompt into Gemini themselves.

Implemented as a manual function-calling loop over `generate_content_stream`,
which yields NDJSON events the FastAPI route wraps in a StreamingResponse.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Iterator

from google import genai
from google.genai import types

from backend import tiktok
from backend.config import settings

# --- KREA persona ------------------------------------------------------------

KREA_PERSONA = """\
Kamu adalah KREA — asisten riset produk & prompt video untuk kreator TikTok.
Satu sesi denganmu punya TIGA bagian berurutan:

BAGIAN 1 — RISET PRODUK
- User menyebut bidang/niche yang diminati (mis. "skincare", "gadget dapur").
- Panggil tool `search_tiktok` dengan kata kunci yang relevan untuk melihat
  konten/tren yang sedang jalan di TikTok di bidang itu.
- Dari data itu + pengetahuanmu, ajak user brainstorming: rangkum tren yang
  terlihat, lalu usulkan beberapa PRODUK konkret yang potensial untuk dibuatkan
  konten (sertakan alasan singkat per produk: kenapa lagi naik / cocok).
- Kalau `search_tiktok` mengembalikan error (mis. RAPIDAPI_KEY belum diset),
  sampaikan singkat ke user lalu tetap bantu brainstorming dari pengetahuan umum.
- Bantu user sampai ia MEMILIH satu produk.

BAGIAN 2 — PROMPT VIDEO
- Setelah user memilih satu produk, buat sebuah PROMPT VIDEO yang siap di-paste
  ke generator video (Gemini). Ajukan lewat tool `make_video_prompt`.
- Prompt video harus deskriptif & sinematik: subjek/produk, adegan/aksi, gaya
  visual, pencahayaan, gerak kamera, mood, dan durasi/aspek bila relevan —
  ditulis sebagai satu blok teks yang langsung bisa dipakai.

BAGIAN 3 — COPY KE GEMINI
- KREA TIDAK membuat videonya. Setelah `make_video_prompt`, beri instruksi
  singkat: salin prompt itu dan tempel ke Gemini untuk men-generate videonya.
- Jangan klaim videonya sudah dibuat.

Aturan umum:
- Selalu Bahasa Indonesia, ramah, to the point.
- Jangan langsung loncat ke prompt video sebelum user memilih produk.
- Setelah memanggil `make_video_prompt`, JANGAN menulis ulang seluruh prompt
  sebagai teks biasa (frontend sudah menampilkannya dengan tombol Salin) —
  cukup kalimat penutup singkat + instruksi copy ke Gemini.
"""


# --- Tools exposed to the orchestrator --------------------------------------
# These JSON schemas are reused directly as Gemini parameters_json_schema.

TOOLS_JSON: list[dict[str, Any]] = [
    {
        "name": "search_tiktok",
        "description": "Search live TikTok content for a niche/keyword to research trending products and angles (part 1). Returns simplified trending videos with engagement stats.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Search keywords / niche, e.g. 'skincare viral' or 'gadget dapur'.",
                },
                "count": {
                    "type": "integer",
                    "description": "How many videos to fetch (default 15, max 30).",
                },
            },
            "required": ["keywords"],
        },
    },
    {
        "name": "make_video_prompt",
        "description": "Produce a finished, ready-to-paste video-generation prompt for the product the user chose (part 2). This does NOT generate a video — the user pastes it into Gemini themselves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product": {"type": "string", "description": "The chosen product the video is about."},
                "concept": {"type": "string", "description": "One-line concept/angle of the video."},
                "video_prompt": {
                    "type": "string",
                    "description": "The full, descriptive, cinematic prompt to paste into Gemini's video generator.",
                },
            },
            "required": ["product", "video_prompt"],
        },
    },
]


def _build_tool() -> types.Tool:
    declarations = []
    for t in TOOLS_JSON:
        schema = t["input_schema"]
        params = schema if schema.get("properties") else None
        declarations.append(
            types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters_json_schema=params,
            )
        )
    return types.Tool(function_declarations=declarations)


_TOOL = _build_tool()


def _dispatch_tool(
    name: str, tool_input: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Execute a tool. Returns (result_for_model, optional_frontend_event)."""
    tool_input = tool_input or {}
    if name == "search_tiktok":
        result = tiktok.search(
            keywords=tool_input.get("keywords", ""),
            count=tool_input.get("count", 15),
        )
        return result, None
    if name == "make_video_prompt":
        event = {
            "type": "video_prompt",
            "product": tool_input.get("product", ""),
            "concept": tool_input.get("concept", ""),
            "video_prompt": tool_input.get("video_prompt", ""),
        }
        return {
            "status": "Prompt video sudah ditampilkan ke user dengan tombol Salin. "
            "Ingatkan user untuk menempelnya ke Gemini. Jangan klaim video sudah dibuat."
        }, event
    return {"error": f"unknown tool '{name}'"}, None


# --- Session store -----------------------------------------------------------
# In-memory conversation history per session (list of Gemini Content turns).
# Fine for personal/single-user MVP; swap for a persistent store if needed later.
SESSIONS: dict[str, list[types.Content]] = {}


def _ndjson(obj: dict[str, Any]) -> bytes:
    return (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")


def stream_chat(
    user_message: str,
    session_id: str | None = None,
) -> Iterator[bytes]:
    """Stream a chat turn as NDJSON events.

    Event types: {"type":"text","text":...},
    {"type":"video_prompt","product":...,"concept":...,"video_prompt":...},
    {"type":"error","error":...}, {"type":"done","session_id":...}.
    """
    session_id = session_id or uuid.uuid4().hex

    if not settings.google_api_key:
        yield _ndjson(
            {"type": "error", "error": "GOOGLE_API_KEY belum diset. Isi file .env dulu."}
        )
        yield _ndjson({"type": "done", "session_id": session_id})
        return

    contents = SESSIONS.setdefault(session_id, [])
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    client = genai.Client(api_key=settings.google_api_key)
    config = types.GenerateContentConfig(
        system_instruction=KREA_PERSONA,
        tools=[_TOOL],
        max_output_tokens=settings.max_tokens,
        # We run the function-call loop ourselves (to call TikTok + emit events).
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    try:
        # Function-call loop: keep going while the model requests tools.
        while True:
            text_buf = ""
            model_parts: list[types.Part] = []  # preserves function_call parts (+ thought signatures)
            function_calls: list[Any] = []

            for chunk in client.models.generate_content_stream(
                model=settings.model, contents=contents, config=config
            ):
                for cand in chunk.candidates or []:
                    content = cand.content
                    if not content or not content.parts:
                        continue
                    for part in content.parts:
                        # Skip thinking/"thought" parts — don't leak reasoning to the user.
                        if getattr(part, "text", None) and not getattr(part, "thought", False):
                            text_buf += part.text
                            yield _ndjson({"type": "text", "text": part.text})
                        if getattr(part, "function_call", None):
                            function_calls.append(part.function_call)
                            model_parts.append(part)

            # Record the model's turn in history (text first, then function_call parts).
            turn_parts: list[types.Part] = []
            if text_buf:
                turn_parts.append(types.Part(text=text_buf))
            turn_parts.extend(model_parts)
            if turn_parts:
                contents.append(types.Content(role="model", parts=turn_parts))

            if not function_calls:
                break

            response_parts = []
            for fc in function_calls:
                args = dict(fc.args) if fc.args else {}
                result, frontend_event = _dispatch_tool(fc.name, args)
                if frontend_event is not None:
                    yield _ndjson(frontend_event)
                response = result if isinstance(result, dict) else {"result": result}
                response_parts.append(
                    types.Part.from_function_response(name=fc.name, response=response)
                )
            contents.append(types.Content(role="user", parts=response_parts))

    except Exception as exc:  # noqa: BLE001
        yield _ndjson({"type": "error", "error": f"Gemini error: {exc}"})

    yield _ndjson({"type": "done", "session_id": session_id})
