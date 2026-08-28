"""POST /api/webhook/telegram

Reemplaza a /api/webhook/mensajeria del documento de arquitectura, usando
Telegram como canal para el MVP de la hackathon: recibe todos los mensajes
entrantes (productores y compradores) y los enruta al agente correcto.
"""
import logging

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from agroia.agents.agente1_recepcion import CONVERSACIONES, procesar_mensaje_productor
from agroia.agents.agente2_estructuracion import (
    OfertaInvalidaError,
    ResultadoEstructuracion,
    estructurar_y_guardar,
)
from agroia.agents.agente3_ventas import atender_consulta_comprador
from agroia.agents.clasificador_intencion import COMPRA, DESCONOCIDA, clasificar_intencion
from agroia.integrations.speech_to_text import transcribir_audio
from agroia.integrations.telegram_client import download_file, get_file_path, parse_update, send_message
from agroia.repositories.productos_repository import ErrorPersistencia

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

# Lo que responde el bot cuando no logra deducir si el usuario quiere comprar
# o vender (un "hola", una pregunta suelta). Antes se asumía "venta" por
# defecto y el bot arrancaba preguntando qué producto ofrecía, aunque la
# persona solo hubiera saludado.
_MENU_INTENCION = (
    "¡Hola! Soy AgroIA Casanare, el mercado campesino del Llano. "
    "Te puedo ayudar con dos cosas:\n\n"
    "• VENDER: cuéntame qué tienes y lo publico en el catálogo. "
    'Por ejemplo: "Tengo 20 kg de plátano a 2.000 el kilo en Yopal".\n'
    "• COMPRAR: dime qué buscas y te muestro quién lo tiene. "
    'Por ejemplo: "Busco plátano por Yopal".\n\n'
    "¿Qué quieres hacer?"
)


@router.post("/telegram")
async def webhook_telegram(update: dict):
    """Recibe el update de Telegram, transcribe el audio si lo hay y enruta
    según la intención: compra -> Agente 3, venta -> Agente 1 + 2, y si no se
    puede deducir, se le pregunta al usuario en vez de adivinar.

    Para el demo real conviene tener dos bots separados (productores /
    compradores) como describe la arquitectura.
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

    # Si ya está a mitad de publicar una oferta, sus mensajes son respuestas a
    # lo que le preguntó el Agente 1 ("Yopal", "3001234567"): clasificarlos
    # aisladamente daría "desconocida" y lo sacaría de la conversación.
    if str(chat_id) not in CONVERSACIONES:
        intencion = await run_in_threadpool(clasificar_intencion, texto)

        if intencion == DESCONOCIDA:
            await send_message(chat_id, _MENU_INTENCION)
            return {"ok": True, "flujo": "desconocida"}

        if intencion == COMPRA:
            # atender_consulta_comprador es síncrona (SDK del LLM bloqueante):
            # se corre en threadpool para no bloquear el event loop.
            resultado = await run_in_threadpool(atender_consulta_comprador, texto)
            await send_message(chat_id, resultado.respuesta_texto)
            return {"ok": True, "flujo": "compra", "resultados": len(resultado.resultados)}

    # Flujo productor (Agente 1 -> Agente 2)
    oferta = await run_in_threadpool(procesar_mensaje_productor, str(chat_id), texto)

    if not oferta.completo:
        await send_message(chat_id, oferta.pregunta_faltante)
        return {"ok": True, "flujo": "productor", "completo": False}

    try:
        # estructurar_y_guardar es síncrona (SDK/DB bloqueantes): threadpool.
        resultado = await run_in_threadpool(
            estructurar_y_guardar,
            oferta,
            telegram_user_id=str(chat_id),
            nombre_productor=oferta.nombre_productor,
            telefono_contacto=oferta.telefono_contacto,
            direccion_local=oferta.direccion_local,
        )
    except OfertaInvalidaError as exc:
        # El Agente 1 la dio por completa pero algo no cuadra (ej. un precio
        # en cero). Se le devuelve al productor en vez de fallar en silencio.
        await send_message(chat_id, "No pude publicar la oferta. " + " ".join(exc.errores))
        return {"ok": True, "flujo": "productor", "completo": False, "errores": exc.errores}
    except ErrorPersistencia:
        # La base de datos no aceptó la escritura. El detalle queda en los logs;
        # al campesino se le dice algo accionable, no un error técnico.
        logger.exception("Fallo de persistencia al publicar la oferta de %s", chat_id)
        await send_message(
            chat_id,
            "Tuve un problema guardando tu oferta. Vuelve a enviarla en un momento, por favor.",
        )
        return {"ok": False, "flujo": "productor", "error": "persistencia"}

    await send_message(chat_id, _confirmacion(resultado))
    return {
        "ok": True,
        "flujo": "productor",
        "completo": True,
        "id": resultado.registro["id"],
        "actualizada": resultado.actualizada,
    }


def _pesos(valor: float) -> str:
    """2000.0 -> '$2.000' (separador de miles colombiano)."""
    return "$" + f"{valor:,.0f}".replace(",", ".")


def _confirmacion(resultado: ResultadoEstructuracion) -> str:
    """Le confirma al productor lo que quedó publicado, usando los campos ya
    estandarizados por el Agente 2. Mostrarle el precio por unidad base
    ("$2.000 por kg" cuando él dijo "$25.000 la arroba") es la forma más
    directa de que valide que lo entendimos bien."""
    registro = resultado.registro

    if resultado.actualizada:
        mensaje = f"¡Listo! Actualicé tu oferta de {registro['producto']}."
    else:
        mensaje = f"¡Listo! Publiqué tu oferta de {registro['producto']} en el catálogo."

    precio_base = registro.get("precio_por_unidad_base")
    if precio_base:
        mensaje += f" Quedó a {_pesos(precio_base)} por {registro['unidad_base']}."

    return mensaje + " Los compradores ya pueden verla y contactarte."
