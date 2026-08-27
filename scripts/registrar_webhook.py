"""Utilidad de una sola vez: registra la URL pública del backend como webhook
de Telegram. Ejecutar DESPUÉS de desplegar (o de levantar un túnel HTTPS
local con ngrok/cloudflared), desde la raíz del proyecto:

    python -m scripts.registrar_webhook
"""
import httpx

from agroia.core.config import settings

if __name__ == "__main__":
    if not settings.TELEGRAM_WEBHOOK_URL:
        raise SystemExit("Define TELEGRAM_WEBHOOK_URL en tu .env antes de ejecutar esto.")

    url = f"{settings.TELEGRAM_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
    resp = httpx.post(url, json={"url": settings.TELEGRAM_WEBHOOK_URL})
    resp.raise_for_status()
    print(resp.json())
