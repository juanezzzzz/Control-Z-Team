"""Síntesis de voz (texto -> audio) con la voz colombiana de Edge TTS.

Se eligió `edge-tts` sobre las alternativas por tres razones prácticas para
la hackathon:
  - Es gratis y no pide API key ni tarjeta (una variable menos que configurar
    en Render).
  - Tiene voz colombiana neutra (`es-CO-GonzaloNeural`), que es la base del
    tono llanero: una voz de España o de México rompe la ilusión de inmediato.
  - Devuelve el audio en streaming, sin escribir archivos temporales.

El tono llanero no lo da el sintetizador sino dos capas juntas: la voz
colombiana + la redacción y el ritmo (ver `agroia/core/voz.py`). Se habla un
poco más lento y un tono más grave que el default, que suena apurado y
demasiado "call center" para el campo.
"""
import asyncio
import logging

import edge_tts

from agroia.core.config import settings

logger = logging.getLogger(__name__)


async def sintetizar(texto: str) -> bytes | None:
    """Devuelve el audio MP3 del texto, o None si la síntesis falla.

    Nunca lanza excepción a propósito: la nota de voz es un extra sobre el
    mensaje escrito, que siempre se envía. Si el servicio de voz no responde,
    el productor igual recibe su respuesta por texto — quedarse sin contestar
    sería mucho peor que contestar sin audio.
    """
    texto = (texto or "").strip()
    if not texto:
        return None

    try:
        comunicacion = edge_tts.Communicate(
            texto,
            settings.TTS_VOZ,
            rate=settings.TTS_VELOCIDAD,
            pitch=settings.TTS_TONO,
        )
        audio = bytearray()
        async for bloque in comunicacion.stream():
            if bloque["type"] == "audio":
                audio.extend(bloque["data"])
    except Exception:  # noqa: BLE001 — red, servicio caído, texto raro…
        logger.exception("Falló la síntesis de voz; se responde solo por texto")
        return None

    if not audio:
        logger.warning("La síntesis de voz devolvió audio vacío")
        return None

    return bytes(audio)


async def sintetizar_con_limite(texto: str, segundos: float | None = None) -> bytes | None:
    """`sintetizar` con tope de tiempo.

    Telegram reintenta el webhook si tardamos demasiado en responder, y eso
    duplicaría la oferta del productor. Antes que arriesgar eso, se prefiere
    soltar el audio y quedarse con el texto.
    """
    limite = segundos if segundos is not None else settings.TTS_TIMEOUT
    try:
        return await asyncio.wait_for(sintetizar(texto), timeout=limite)
    except asyncio.TimeoutError:
        logger.warning("La síntesis de voz superó %.1fs; se responde solo por texto", limite)
        return None
