"""Configuration for KREA, read from environment / .env.

Nothing secret is hardcoded here — the Google AI Studio API key, the RapidAPI
key, and the model choice all come from environment variables (see .env.example).
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- Model (Google AI Studio / Gemini API) ---------------------------------
    # Auth to Google AI Studio. Never hardcode — read from env.
    # Accepts GOOGLE_API_KEY or the common GEMINI_API_KEY alias.
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")

    # Single model for the whole app. KREA runs on Google Gemma 4 31B.
    model: str = os.getenv("MODEL", "gemma-4-31b-it")

    # Max output tokens for a single model turn.
    max_tokens: int = int(os.getenv("MAX_TOKENS", "8192"))

    # --- TikTok research data (RapidAPI) --------------------------------------
    # Used by part 1 (product research). Get a key at https://rapidapi.com and
    # subscribe to a TikTok scraper API, then set RAPIDAPI_KEY in .env.
    # Host/path default to the popular "tiktok-scraper7" API; change them if you
    # subscribe to a different provider.
    rapidapi_key: str = os.getenv("RAPIDAPI_KEY", "")
    rapidapi_host: str = os.getenv("RAPIDAPI_HOST", "tiktok-scraper7.p.rapidapi.com")
    tiktok_search_path: str = os.getenv("TIKTOK_SEARCH_PATH", "/feed/search")
    # Some providers name the keyword param "keywords", others "keyword".
    tiktok_query_param: str = os.getenv("TIKTOK_QUERY_PARAM", "keywords")
    tiktok_region: str = os.getenv("TIKTOK_REGION", "ID")

    # --- Web server -----------------------------------------------------------
    # CORS origins for the Vite frontend.
    cors_origins: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()
    ]


settings = Settings()
