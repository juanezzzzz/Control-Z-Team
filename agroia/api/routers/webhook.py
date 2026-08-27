"""POST /api/webhook/telegram

Reemplaza a /api/webhook/mensajeria del documento de arquitectura, usando
Telegram como canal para el MVP de la hackathon: recibe todos los mensajes
entrantes (productores y compradores) y los enruta al agente correcto.
"""
from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from agroia.agents.agente1_recepcion import procesar_mensaje_productor
from agroia.agents.agente2_estructuracion import estructurar_y_guardar
from agroia.agents.agente3_ventas import atender_consulta_comprador
from agroia.core.text_utils import normalizar
from agroia.integrations.speech_to_text import transcribir_audio
from agroia.integrations.telegram_client import download_file, get_file_path, parse_update, send_message

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

# Heurística de enrutamiento del MVP: si el mensaje expresa intención de
# COMPRA se manda al Agente 3; si no, se trata como oferta de un productor
# (Agente 1 + 2). Para el demo real conviene tener dos bots separados.
_INTENCION_COMPRA = (
    "busco", "buscando", "necesito", "necesitando", "quiero comprar",
    "estoy buscando", "alguien vende", "alguien tiene", "donde consigo",
    "donde puedo conseguir", "hay ", "quien vende", "me interesa comprar",
)
_INTENCION_VENTA = ("vendo", "tengo", "ofrezco", "quiero vender", "estoy vendiendo", "dispongo de")


def _es_intencion_compra(texto: str) -> bool:
    t = normalizar(texto)
    if any(t.startswith(p) or f" {p}" in f" {t}" for p in _INTENCION_VENTA):
        return False
    return any(t.startswith(p) or f" {p}" in f" {t}" for p in _INTENCION_COMPRA)


@router.post("/telegram")
async def webhook_telegram(update: dict):
    """Recibe el update de Telegram, transcribe el audio si lo hay y enruta:
    intención de compra -> Agente 3; cualquier otra cosa -> Agente 1 + 2
    (ver `_es_intencion_compra`). Para el demo real conviene tener dos bots
    separados (productores / compradores) como describe la arquitectura.
    """
    parsed = parse_update(update)
    if not parsed:
        return {"ok": True}  # update irrelevante (ej. bot añadido a un grupo)

    chat_id = parsed["chat_id"]

    if parsed["tipo"] == "audio":
        file_path = await get_file_path(parsed["voice_file_id"])
        audio_bytes = await download_file(file_path)
        texto = await run_in_threadpool(transcribir_audio, audio_bytes)
    else:
        texto = parsed["texto"]

    if not texto or not texto.strip():
        return {"ok": True, "flujo": "ninguno"}

    if _es_intencion_compra(texto):
        # atender_consulta_comprador es síncrona (SDK de Claude bloqueante):
        # se corre en threadpool para no bloquear el event loop.
        resultado = await run_in_threadpool(atender_consulta_comprador, texto)
        await send_message(chat_id, resultado.respuesta_texto)
        return {"ok": True, "flujo": "compra", "resultados": len(resultado.resultados)}

    # Flujo productor (Agente 1 -> Agente 2)
    oferta = await run_in_threadpool(procesar_mensaje_productor, str(chat_id), texto)

    if not oferta.completo:
        await send_message(chat_id, oferta.pregunta_faltante)
        return {"ok": True, "flujo": "productor", "completo": False}

    registro = await run_in_threadpool(estructurar_y_guardar, oferta, str(chat_id))
    await send_message(
        chat_id,
        f"¡Listo! Publiqué tu oferta de {oferta.producto} en el catálogo. "
        f"Los compradores ya pueden verla y contactarte.",
    )
    return {"ok": True, "flujo": "productor", "completo": True, "id": registro["id"]}
