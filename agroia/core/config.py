"""Configuración centralizada de la app, cargada desde variables de entorno (.env).

Todo el resto del código importa `settings` desde aquí — es el único lugar
que debería llamar a `os.getenv`.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "")
    TELEGRAM_API_BASE = "https://api.telegram.org"

    # Anthropic (Claude) — usado por Agente 3 (ventas)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL_VENTAS = os.getenv("CLAUDE_MODEL_VENTAS", "claude-sonnet-4-5")
    CLAUDE_MODEL_CLASIFICACION = os.getenv("CLAUDE_MODEL_CLASIFICACION", "claude-haiku-4-5")

    # Gemini — usado por Agente 1 (recepción/extracción)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL_EXTRACCION = os.getenv("GEMINI_MODEL_EXTRACCION", "gemini-3.6-flash")

    # Groq (STT)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3")

    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    SUPABASE_TABLE_PRODUCTOS = os.getenv("SUPABASE_TABLE_PRODUCTOS", "productos")

    # App
    APP_ENV = os.getenv("APP_ENV", "development")
    CORS_ALLOW_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")]


settings = Settings()
