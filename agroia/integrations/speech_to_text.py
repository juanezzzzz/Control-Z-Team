"""Transcripción de voz a texto usando Groq (Whisper-large-v3).

Groq se eligió sobre openai-whisper local porque en el entorno de una
hackathon (sin GPU garantizada) la API de Groq transcribe en milisegundos
y tiene una capa gratuita generosa.
"""
import io
from groq import Groq

from agroia.core.config import settings

_client = Groq(api_key=settings.GROQ_API_KEY)


def transcribir_audio(audio_bytes: bytes, filename: str = "nota_voz.ogg") -> str:
    """Recibe los bytes crudos del .ogg de Telegram y devuelve el texto transcrito."""
    resultado = _client.audio.transcriptions.create(
        file=(filename, io.BytesIO(audio_bytes)),
        model=settings.GROQ_STT_MODEL,
        language="es",
        response_format="text",
    )
    # El SDK de Groq devuelve un string cuando response_format="text"
    return str(resultado).strip()
