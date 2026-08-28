"""Configuración centralizada de la app, cargada desde variables de entorno (.env).

Todo el resto del código importa `settings` desde aquí — es el único lugar
que debería llamar a `os.getenv`.

En local las variables se leen del archivo `.env`; en un despliegue (Vercel,
Render, Railway…) se cargan desde el panel del proveedor y `load_dotenv()`
simplemente no encuentra archivo y no hace nada.
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "")
    TELEGRAM_API_BASE = "https://api.telegram.org"

    # LLM — OpenRouter (API compatible con OpenAI). Lo usan el Agente 1
    # (extracción) y el Agente 3 (ventas). Los slugs deepseek/*:free fueron
    # retirados del tier gratuito de OpenRouter (confirmado 2026-08-27); este
    # default es un modelo gratis verificado que sí soporta JSON mode.
    # Catálogo completo: https://openrouter.ai/models
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "minimax/minimax-m3:free")
    LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))

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

    # Panel de administrador (/admin en el frontend). Un solo usuario — ver
    # agroia/core/admin_auth.py. Sin estas dos variables el login rechaza
    # cualquier intento, así que el panel queda deshabilitado por defecto.
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


settings = Settings()


# Sin estas cinco el sistema no arranca de verdad: el bot no responde, los
# agentes no piensan o no hay dónde guardar. Se listan acá para que un
# despliegue mal configurado se detecte en el healthcheck (`GET /`) y no
# con un error críptico a mitad de una conversación con un campesino.
VARIABLES_REQUERIDAS = (
    "TELEGRAM_BOT_TOKEN",
    "OPENROUTER_API_KEY",  # Agente 1 (extracción) y Agente 3 (ventas)
    "GROQ_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
)


def variables_faltantes() -> list[str]:
    """Nombres (nunca valores) de las variables requeridas que están vacías."""
    return [nombre for nombre in VARIABLES_REQUERIDAS if not getattr(settings, nombre)]
