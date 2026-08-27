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

    # Gemini — usado por Agente 1 (recepción/extracción) y Agente 3 (ventas)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL_EXTRACCION = os.getenv("GEMINI_MODEL_EXTRACCION", "gemini-3.6-flash")
    GEMINI_MODEL_VENTAS = os.getenv("GEMINI_MODEL_VENTAS", "gemini-3.6-flash")

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


# Sin estas cinco el sistema no arranca de verdad: el bot no responde, los
# agentes no piensan o no hay dónde guardar. Se listan acá para que un
# despliegue mal configurado se detecte en el healthcheck (`GET /`) y no
# con un error críptico a mitad de una conversación con un campesino.
VARIABLES_REQUERIDAS = (
    "TELEGRAM_BOT_TOKEN",
    "GEMINI_API_KEY",     # Agente 1 (extracción) y Agente 3 (ventas)
    "GROQ_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
)


def variables_faltantes() -> list[str]:
    """Nombres (nunca valores) de las variables requeridas que están vacías."""
    return [nombre for nombre in VARIABLES_REQUERIDAS if not getattr(settings, nombre)]
