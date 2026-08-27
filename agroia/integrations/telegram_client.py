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


def parse_update(update: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Normaliza un update de Telegram a {chat_id, tipo, texto|voice_file_id}.

    Devuelve None si el update no trae un mensaje utilizable (ej. un evento
    de "bot añadido a un grupo", edición de mensaje, etc.).
    """
    message = update.get("message")
    if not message:
        return None

    chat_id = message["chat"]["id"]

    if "voice" in message:
        return {"chat_id": chat_id, "tipo": "audio", "voice_file_id": message["voice"]["file_id"]}

    if "text" in message:
        return {"chat_id": chat_id, "tipo": "texto", "texto": message["text"]}

    return None
