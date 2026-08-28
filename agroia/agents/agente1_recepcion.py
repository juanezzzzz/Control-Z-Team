"""Agente 1: Recepción y Extracción de Datos (Productor).

Flujo (según el documento de arquitectura, sección 3):
 1. Si el mensaje es audio, ya llega transcrito a texto (ver
    agroia/integrations/speech_to_text.py).
 2. Extrae producto, cantidad, precio, ubicación, nombre y teléfono de
    contacto con el LLM (vía OpenRouter, en JSON mode).
 3. Si falta algún dato obligatorio, arma una respuesta humanizada (saluda
    según la hora en el primer mensaje, reconoce lo que ya contó el
    productor y pregunta TODO lo que falta en una sola frase, no campo por
    campo) y el router de webhook la reenvía por Telegram; el estado
    parcial se guarda en memoria (CONVERSACIONES) hasta completar los 6
    campos.

Nota de producción: el diccionario en memoria se pierde si el proceso se
reinicia. Para el MVP de hackathon es suficiente; si sobra tiempo, se puede
mover a una tabla `conversaciones` en Supabase con el mismo esquema.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from agroia.integrations.llm_client import LLMError, pedir_json
from agroia.schemas import OfertaExtraida

logger = logging.getLogger(__name__)

# Colombia es UTC-5 todo el año (no tiene horario de verano), así que un
# offset fijo alcanza y evita depender del paquete `tzdata` en Windows.
_HORA_COLOMBIA = timezone(timedelta(hours=-5))

# Estado conversacional simple: chat_id -> datos parciales acumulados
CONVERSACIONES: dict[str, dict[str, Any]] = {}

CAMPOS_OBLIGATORIOS = [
    "producto", "cantidad", "precio", "ubicacion", "nombre_productor", "telefono_contacto",
]
CAMPOS_EXTRAIBLES = (
    "producto", "cantidad", "unidad", "precio", "ubicacion",
    "nombre_productor", "telefono_contacto",
)

SYSTEM_PROMPT = """Eres el Agente 1 de AgroIA Casanare: extraes datos estructurados
de ofertas de productos agropecuarios que campesinos escriben en lenguaje natural
(texto libre, a veces ya transcrito de una nota de voz).

Respondé ÚNICAMENTE con un objeto JSON válido, sin texto adicional, con esta forma:
{
  "producto": string o null,
  "cantidad": number o null,
  "unidad": string o null,
  "precio": number o null,
  "ubicacion": string o null,
  "nombre_productor": string o null,
  "telefono_contacto": string o null
}

Reglas:
- "unidad": ej. "kg", "litros", "arrobas", "unidades".
- "precio": precio unitario en pesos colombianos, solo el número.
- "ubicacion": vereda o municipio, ej. "Yopal", "Aguazul".
- "nombre_productor": el nombre de la persona que ofrece el producto (quien
  escribe), ej. "Juan Pérez". No es el nombre del producto ni del comprador.
- "telefono_contacto": el número de teléfono o WhatsApp donde los compradores
  pueden contactar al productor. Solo dígitos (con indicativo si lo da, ej.
  "573001234567"); quita espacios, guiones y símbolos.
- Si el mensaje no menciona un dato, dejá ese campo en null. No inventes valores.
- "cantidad" y "precio" deben ser números (sin símbolos de moneda ni texto).
- Combiná la información nueva del mensaje con los datos que ya se tenían
  (te los paso como contexto) para ir completando la oferta.
"""


def _extraer_con_llm(mensaje: str, datos_previos: dict[str, Any]) -> dict[str, Any]:
    """Devuelve los campos que el modelo logró extraer. `{}` si el modelo
    falló o no devolvió nada aprovechable (el flujo simplemente vuelve a
    preguntar por lo que falte)."""
    contexto = (
        f"Datos ya conocidos de esta oferta: {json.dumps(datos_previos, ensure_ascii=False)}\n"
        f'Nuevo mensaje del productor: "{mensaje}"'
    )
    try:
        datos = pedir_json(SYSTEM_PROMPT, contexto)
    except LLMError:
        logger.warning("Agente 1: el modelo no devolvió datos para %r", mensaje, exc_info=True)
        return {}
    return {k: datos.get(k) for k in CAMPOS_EXTRAIBLES if datos.get(k) is not None}


_FRASES_CAMPO_FALTANTE = {
    "producto": "qué producto ofreces",
    "cantidad": "qué cantidad tienes disponible (por ejemplo, 20 kg o 5 arrobas)",
    "precio": "a qué precio lo vendes",
    "ubicacion": "desde qué vereda o municipio lo ofreces",
    "nombre_productor": "cuál es tu nombre",
    "telefono_contacto": "a qué número de teléfono o WhatsApp te pueden contactar los compradores",
}


def _saludo_segun_hora() -> str:
    """Saludo natural según la hora local en Colombia."""
    hora = datetime.now(_HORA_COLOMBIA).hour
    if 5 <= hora < 12:
        return "¡Buenos días!"
    if 12 <= hora < 19:
        return "¡Buenas tardes!"
    return "¡Buenas noches!"


def _unir_en_espanol(frases: list[str]) -> str:
    """['a', 'b', 'c'] -> 'a, b y c' (y ['a'] -> 'a')."""
    if len(frases) == 1:
        return frases[0]
    return ", ".join(frases[:-1]) + " y " + frases[-1]


def _resumen_lo_ya_dicho(datos: dict[str, Any]) -> str | None:
    """Frase corta reconociendo lo que el productor ya contó (ej. "4 kg de
    papa"), para que la respuesta no ignore lo que acaba de escribir."""
    if not datos.get("producto"):
        return None
    cantidad = datos.get("cantidad")
    if cantidad:
        unidad = datos.get("unidad") or "kg"
        return f"{cantidad:g} {unidad} de {datos['producto']}"
    return str(datos["producto"])


def _mensaje_pregunta_faltantes(
    datos: dict[str, Any], campos_faltantes: list[str], es_primer_mensaje: bool
) -> str:
    """Arma una respuesta educada y natural pidiendo TODO lo que falta en una
    sola frase (en vez de un campo por mensaje), saludando según la hora si
    es el primer mensaje de la conversación y reconociendo lo que ya se sabe."""
    pregunta = f"¿Me podrías decir {_unir_en_espanol([_FRASES_CAMPO_FALTANTE[c] for c in campos_faltantes])}?"
    resumen = _resumen_lo_ya_dicho(datos)

    partes = []
    if es_primer_mensaje:
        partes.append(_saludo_segun_hora())
        partes.append(
            f"Perfecto, ya tengo anotado que ofreces {resumen}."
            if resumen else "Con gusto te ayudo a publicar tu oferta."
        )
    elif resumen:
        partes.append(f"¡Gracias! Ya tengo anotado que ofreces {resumen}.")
    else:
        partes.append("¡Gracias!")
    partes.append(pregunta)
    return " ".join(partes)


def procesar_mensaje_productor(chat_id: str, mensaje: str) -> OfertaExtraida:
    """Punto de entrada del Agente 1. Acumula estado por chat_id hasta que
    la oferta tiene los 6 campos obligatorios."""
    es_primer_mensaje = chat_id not in CONVERSACIONES
    datos_previos = CONVERSACIONES.get(chat_id, {})
    datos_nuevos = _extraer_con_llm(mensaje, datos_previos)

    # Merge: un dato nuevo no-nulo sobreescribe al previo
    datos_combinados = {**datos_previos, **datos_nuevos}
    CONVERSACIONES[chat_id] = datos_combinados

    campos_faltantes = [c for c in CAMPOS_OBLIGATORIOS if not datos_combinados.get(c)]

    if campos_faltantes:
        return OfertaExtraida(
            **datos_combinados,
            completo=False,
            pregunta_faltante=_mensaje_pregunta_faltantes(
                datos_combinados, campos_faltantes, es_primer_mensaje
            ),
        )

    # Oferta completa: limpiar el estado conversacional
    CONVERSACIONES.pop(chat_id, None)
    return OfertaExtraida(**datos_combinados, completo=True)
