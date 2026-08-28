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

    # Groq — voz a texto (entrada: notas de voz del productor)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3")

    # Edge TTS — texto a voz (salida: el bot contesta hablando).
    # No necesita API key. `es-CO-GonzaloNeural` es la voz colombiana neutra:
    # la base del tono llanero, junto con la redacción de agroia/core/voz.py.
    # La velocidad y el tono se bajan un poco respecto al default, que suena
    # apurado y demasiado "call center" para hablarle a alguien en el campo.
    #
    # Activa: el bot responde SIEMPRE con texto + nota de voz, sin importar
    # si la persona escribió o habló. En false vuelve a ser solo texto.
    VOZ_RESPUESTA_ACTIVA = os.getenv("VOZ_RESPUESTA_ACTIVA", "true").lower() in ("1", "true", "si", "sí")
    TTS_VOZ = os.getenv("TTS_VOZ", "es-CO-GonzaloNeural")
    TTS_VELOCIDAD = os.getenv("TTS_VELOCIDAD", "-8%")
    TTS_TONO = os.getenv("TTS_TONO", "-2Hz")
    TTS_TIMEOUT = float(os.getenv("TTS_TIMEOUT", "12"))

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
    "OPENROUTER_API_KEY",  # Agente 1 (extracción) y Agente 3 (ventas)
    "GROQ_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
)


def variables_faltantes() -> list[str]:
    """Nombres (nunca valores) de las variables requeridas que están vacías."""
    return [nombre for nombre in VARIABLES_REQUERIDAS if not getattr(settings, nombre)]
