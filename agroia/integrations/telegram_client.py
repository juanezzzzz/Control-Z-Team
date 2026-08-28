"""Cliente delgado sobre la Telegram Bot API (HTTP puro vía httpx).

No usamos un framework de bots a propósito: el webhook ya lo maneja
FastAPI (ver agroia/api/routers/webhook.py), y aquí solo necesitamos 3
operaciones: enviar texto, obtener la ruta de un archivo (nota de voz) y
descargarlo.
"""
from typing import Any, Optional
import httpx

from agroia.core.config import settings

BASE = f"{settings.TELEGRAM_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}"


async def send_message(chat_id: int | str, text: str) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{BASE}/sendMessage", json={"chat_id": chat_id, "text": text})
        resp.raise_for_status()


async def send_voice(chat_id: int | str, audio: bytes) -> bool:
    """Envía el audio como nota de voz. Devuelve True si Telegram lo aceptó.

    Se intenta primero `sendVoice` (se ve como la burbuja de nota de voz, que
    es lo natural para responderle a alguien que habló) y si Telegram rechaza
    el formato se reintenta con `sendAudio`, que acepta MP3 sin discutir. El
    sintetizador entrega MP3 y no OGG/OPUS, y convertir exigiría ffmpeg dentro
    del contenedor — este doble intento evita esa dependencia.

    Nunca lanza: el audio es un extra sobre el mensaje escrito.
    """
    archivo = {"voice": ("respuesta.mp3", audio, "audio/mpeg")}
    datos = {"chat_id": str(chat_id)}

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{BASE}/sendVoice", data=datos, files=archivo)
            if resp.status_code == 200:
                return True

            resp = await client.post(
                f"{BASE}/sendAudio",
                data=datos,
                files={"audio": ("respuesta.mp3", audio, "audio/mpeg")},
            )
            return resp.status_code == 200
        except httpx.HTTPError:
            return False


async def get_file_path(file_id: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BASE}/getFile", params={"file_id": file_id})
        resp.raise_for_status()
        return resp.json()["result"]["file_path"]


async def download_file(file_path: str) -> bytes:
    file_url = f"{settings.TELEGRAM_API_BASE}/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(file_url)
        resp.raise_for_status()
        return resp.content


# Adjuntos que el bot todavía no procesa, con el nombre que se usa al
# responderle a la persona. El orden importa: un GIF llega como `animation`
# Y como `document`, y hay que nombrarlo por lo primero.
_ADJUNTOS_NO_SOPORTADOS = (
    ("photo", "una foto"),
    ("animation", "un GIF"),
    ("video_note", "un video"),
    ("video", "un video"),
    ("sticker", "un sticker"),
    ("audio", "un archivo de audio"),
    ("document", "un archivo"),
    ("location", "una ubicación"),
    ("contact", "un contacto"),
    ("poll", "una encuesta"),
)


def parse_update(update: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Normaliza un update de Telegram a {chat_id, tipo, ...}.

    `tipo` puede ser:
      - "texto"        -> trae `texto`
      - "audio"        -> trae `voice_file_id` (nota de voz, se transcribe)
      - "no_soportado" -> trae `adjunto`, el nombre legible de lo que mandó

    Devuelve None solo si el update no involucra un mensaje de una persona
    (ej. "bot añadido a un grupo", edición de mensaje): ahí no hay a quién
    responderle. Un adjunto que no sabemos procesar SÍ devuelve algo, para
    que el bot pueda contestar en vez de quedarse callado.
    """
    message = update.get("message")
    if not message:
        return None

    chat_id = message["chat"]["id"]

    if "voice" in message:
        return {"chat_id": chat_id, "tipo": "audio", "voice_file_id": message["voice"]["file_id"]}

    if "text" in message:
        return {"chat_id": chat_id, "tipo": "texto", "texto": message["text"]}

    # Foto o video CON descripción: la descripción es el mensaje de verdad.
    # Mandar la foto de la cosecha con "vendo 20 kg de papa" es lo natural, y
    # responder "no proceso fotos" ignorando ese texto sería absurdo.
    caption = (message.get("caption") or "").strip()
    if caption:
        return {"chat_id": chat_id, "tipo": "texto", "texto": caption}

    for clave, nombre in _ADJUNTOS_NO_SOPORTADOS:
        if clave in message:
            return {"chat_id": chat_id, "tipo": "no_soportado", "adjunto": nombre}

    return None
