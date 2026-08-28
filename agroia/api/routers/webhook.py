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
from agroia.core.config import settings
from agroia.core.voz import texto_hablado
from agroia.integrations.speech_to_text import transcribir_audio
from agroia.integrations.telegram_client import (
    download_file,
    get_file_path,
    parse_update,
    send_message,
    send_voice,
)
from agroia.integrations.text_to_speech import sintetizar_con_limite
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

# Respuesta a una foto, video o sticker sin descripción. Se le dice qué SÍ
# entiende el bot, no solo qué no puede hacer.
_MENSAJE_NO_SOPORTADO = (
    "Recibí {adjunto}, pero por ahora todavía no puedo interpretar ese tipo "
    "de mensaje. Lo que sí entiendo son mensajes escritos y notas de voz. "
    "¿Me cuentas por ahí qué quieres vender o comprar?\n\n"
    "Un truco: si mandas una foto, escríbele una descripción y yo leo esa "
    "descripción sin problema."
)


async def responder(chat_id: int | str, texto: str) -> None:
    """Le responde al usuario por escrito Y hablado, siempre.

    El texto va primero y nunca falta, por tres razones: llega aunque la
    síntesis falle, se puede releer, y de ahí se copia un teléfono o un
    precio — cosas que una nota de voz no permite. El audio va encima, como
    añadido, no como reemplazo.

    Se manda voz a todo el mundo, no solo a quien escribió por voz: en el
    campo es común que quien lee con dificultad igual escriba como puede, y
    condicionar el audio al canal de entrada dejaría por fuera justo a quien
    más lo necesita. Para volver al bot solo-texto: VOZ_RESPUESTA_ACTIVA=false.
    """
    await send_message(chat_id, texto)

    if not settings.VOZ_RESPUESTA_ACTIVA:
        return

    audio = await sintetizar_con_limite(texto_hablado(texto))
    if audio:
        await send_voice(chat_id, audio)


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

    # Foto, video, sticker… sin descripción: no hay nada que interpretar, pero
    # quedarse callado deja a la persona sin saber si el bot la escuchó.
    if parsed["tipo"] == "no_soportado":
        await responder(chat_id, _MENSAJE_NO_SOPORTADO.format(adjunto=parsed["adjunto"]))
        return {"ok": True, "flujo": "no_soportado"}

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
            await responder(chat_id, _MENU_INTENCION)
            return {"ok": True, "flujo": "desconocida"}

        if intencion == COMPRA:
            # atender_consulta_comprador es síncrona (SDK del LLM bloqueante):
            # se corre en threadpool para no bloquear el event loop.
            resultado = await run_in_threadpool(atender_consulta_comprador, texto)
            await responder(chat_id, resultado.respuesta_texto)
            return {"ok": True, "flujo": "compra", "resultados": len(resultado.resultados)}

    # Flujo productor (Agente 1 -> Agente 2)
    oferta = await run_in_threadpool(procesar_mensaje_productor, str(chat_id), texto)

    if not oferta.completo:
        await responder(chat_id, oferta.pregunta_faltante)
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
        await responder(chat_id, "No pude publicar la oferta. " + " ".join(exc.errores))
        return {"ok": True, "flujo": "productor", "completo": False, "errores": exc.errores}
    except ErrorPersistencia:
        # La base de datos no aceptó la escritura. El detalle queda en los logs;
        # al campesino se le dice algo accionable, no un error técnico.
        logger.exception("Fallo de persistencia al publicar la oferta de %s", chat_id)
        await responder(
            chat_id,
            "Tuve un problema guardando tu oferta. Vuelve a enviarla en un momento, por favor.",
        )
        return {"ok": False, "flujo": "productor", "error": "persistencia"}

    await responder(chat_id, _confirmacion(resultado))
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
