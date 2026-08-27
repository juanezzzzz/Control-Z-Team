"""POST /api/webhook/telegram

Reemplaza a /api/webhook/mensajeria del documento de arquitectura, usando
Telegram como canal para el MVP de la hackathon: recibe todos los mensajes
entrantes (productores y compradores) y los enruta al agente correcto.
"""
from fastapi import APIRouter

from agroia.agents.agente1_recepcion import procesar_mensaje_productor
from agroia.agents.agente2_estructuracion import estructurar_y_guardar
from agroia.agents.agente3_ventas import atender_consulta_comprador
from agroia.integrations.speech_to_text import transcribir_audio
from agroia.integrations.telegram_client import download_file, get_file_path, parse_update, send_message

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

PALABRAS_INTENCION_COMPRA = ("busco", "necesito", "quiero comprar")


@router.post("/telegram")
async def webhook_telegram(update: dict):
    """Heurística simple de enrutamiento para el MVP: si el mensaje empieza
    con "busco"/"necesito" se trata como intención de compra (Agente 3);
    cualquier otro texto/audio se trata como oferta de un productor
    (Agente 1 + 2). Para el demo real conviene tener dos bots/números
    separados (uno para productores, otro para compradores) tal como
    describe el documento de arquitectura.
    """
    parsed = parse_update(update)
    if not parsed:
        return {"ok": True}  # update irrelevante (ej. bot añadido a un grupo)

    chat_id = parsed["chat_id"]

    if parsed["tipo"] == "audio":
        file_path = await get_file_path(parsed["voice_file_id"])
        audio_bytes = await download_file(file_path)
        texto = transcribir_audio(audio_bytes)
    else:
        texto = parsed["texto"]

    texto_lower = texto.lower().strip()

    if texto_lower.startswith(PALABRAS_INTENCION_COMPRA):
        resultado = atender_consulta_comprador(texto)
        await send_message(chat_id, resultado.respuesta_texto)
        return {"ok": True, "flujo": "compra", "resultados": len(resultado.resultados)}

    # Flujo productor (Agente 1 -> Agente 2)
    oferta = procesar_mensaje_productor(str(chat_id), texto)

    if not oferta.completo:
        await send_message(chat_id, oferta.pregunta_faltante)
        return {"ok": True, "flujo": "productor", "completo": False}

    registro = estructurar_y_guardar(oferta, telegram_user_id=str(chat_id))
    await send_message(
        chat_id,
        f"¡Listo! Publiqué tu oferta de {oferta.producto} en el catálogo. "
        f"Los compradores ya pueden verla y contactarte.",
    )
    return {"ok": True, "flujo": "productor", "completo": True, "id": registro["id"]}
